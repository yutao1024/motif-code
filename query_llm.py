class TaskPolicy(UtgBasedInputPolicy):

    def __init__(self, device, app, random_input, task):
        super(TaskPolicy, self).__init__(device, app, random_input)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.task = task

        self.__nav_target = None
        self.__nav_num_steps = -1
        self.__num_restarts = 0
        self.__num_steps_outside = 0
        self.__event_trace = ""
        self.__missed_states = set()
        self.__random_explore = random_input
        self.__action_history = []

    def generate_event_based_on_utg(self):
        """
        generate an event based on current UTG
        @return: InputEvent
        """
        current_state = self.current_state
        self.logger.info("Current state: %s" % current_state.state_str)
        if current_state.state_str in self.__missed_states:
            self.__missed_states.remove(current_state.state_str)

        if current_state.get_app_activity_depth(self.app) < 0:
            # If the app is not in the activity stack
            start_app_intent = self.app.get_start_intent()

            # It seems the app stucks at some state, has been
            # 1) force stopped (START, STOP)
            #    just start the app again by increasing self.__num_restarts
            # 2) started at least once and cannot be started (START)
            #    pass to let viewclient deal with this case
            # 3) nothing
            #    a normal start. clear self.__num_restarts.

            if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
                    or self.__event_trace.endswith(EVENT_FLAG_START_APP):
                self.__num_restarts += 1
                self.logger.info("The app had been restarted %d times.", self.__num_restarts)
            else:
                self.__num_restarts = 0

            # pass (START) through
            if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
                if self.__num_restarts > MAX_NUM_RESTARTS:
                    # If the app had been restarted too many times, enter random mode
                    msg = "The app had been restarted too many times. Entering random mode."
                    self.logger.info(msg)
                    self.__random_explore = True
                else:
                    # Start the app
                    self.__event_trace += EVENT_FLAG_START_APP
                    self.logger.info("Trying to start the app...")
                    self.__action_history = [f'- start the app {self.app.app_name}']
                    return IntentEvent(intent=start_app_intent)

        elif current_state.get_app_activity_depth(self.app) > 0:
            # If the app is in activity stack but is not in foreground
            self.__num_steps_outside += 1

            if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
                # If the app has not been in foreground for too long, try to go back
                if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
                    stop_app_intent = self.app.get_stop_intent()
                    go_back_event = IntentEvent(stop_app_intent)
                else:
                    go_back_event = KeyEvent(name="BACK")
                self.__event_trace += EVENT_FLAG_NAVIGATE
                self.logger.info("Going back to the app...")
                self.__action_history.append('- go back')
                return go_back_event
        else:
            # If the app is in foreground
            self.__num_steps_outside = 0

        action, candidate_actions = self._get_action_with_LLM(current_state, self.__action_history)
        if action is not None:
            self.__action_history.append(current_state.get_action_desc(action))
            return action

        if self.__random_explore:
            self.logger.info("Trying random event.")
            action = random.choice(candidate_actions)
            self.__action_history.append(current_state.get_action_desc(action))
            return action

        # If couldn't find a exploration target, stop the app
        stop_app_intent = self.app.get_stop_intent()
        self.logger.info("Cannot find an exploration target. Trying to restart app...")
        self.__action_history.append('- stop the app')
        self.__event_trace += EVENT_FLAG_STOP_APP
        return IntentEvent(intent=stop_app_intent)
        
    def _query_llm(self, prompt):
        import requests
        URL = os.environ['GPT_URL']  # NOTE: replace with your own GPT API
        body = {"model":"gpt-3.5-turbo","messages":[{"role":"user","content":prompt}],"stream":True}
        headers = {'Content-Type': 'application/json', 'path': 'v1/chat/completions'}
        r = requests.post(url=URL, json=body, headers=headers)
        return r.content.decode()

    def _get_action_with_LLM(self, current_state, action_history):
        task_prompt = f"I'm using a smartphone to {self.task}."
        history_prompt = f'I have already completed the following steps, which should not be performed again: \n ' + ';\n '.join(action_history)
        state_prompt, candidate_actions = current_state.get_described_actions()
        question = 'Which action should I choose next? Just return the action id and nothing else.\nIf no more action is needed, return -1.'
        prompt = f'{task_prompt}\n{state_prompt}\n{history_prompt}\n{question}'
        print(prompt)
        response = self._query_llm(prompt)
        print(f'response: {response}')
        if '-1' in response:
            input(f"Seems the task is completed. Press Enter to continue...")
        match = re.search(r'\d+', response)
        if not match:
            return None, candidate_actions
        idx = int(match.group(0))
        selected_action = candidate_actions[idx]
        if isinstance(selected_action, SetTextEvent):
            view_text = current_state.get_view_desc(selected_action.view)
            question = f'What text should I enter to the {view_text}? Just return the text and nothing else.'
            prompt = f'{task_prompt}\n{state_prompt}\n{question}'
            print(prompt)
            response = self._query_llm(prompt)
            print(f'response: {response}')
            selected_action.text = response.replace('"', '').replace(' ', '-')
            if len(selected_action.text) > 30:  # heuristically disable long text input
                selected_action.text = ''
        return selected_action, candidate_actions