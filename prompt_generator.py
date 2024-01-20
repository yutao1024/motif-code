import copy
import os
import re
def get_described_actions_from_original_view(view_discription):
    """
    Get a text description of current state
    TODO: if include_image_contents, we describe the image element utilizing a multi-modal model 
    """
    # enabled_view_ids = []
    # for id, node in leafnode_discreption.items():
    #     # exclude navigation bar if exists
    #     if self.__safe_dict_get(view_dict, 'visible') and \
    #         self.__safe_dict_get(view_dict, 'resource_id') not in \
    #         ['android:id/navigationBarBackground',
    #         'android:id/statusBarBackground']: 
    #         enabled_view_ids.append(view_dict['temp_id'])
    available_actions = []
    view_descs = []
    # original_target_element_id = target_element_id
    for elementid, element in view_discription.items():
        clickable = element['clickable']
        scrollable = element['scrollable']
        # checkable = self._get_self_ancestors_property(view, 'checkable')
        long_clickable = element['long_clickable']
        editable = 'android.widget.EditText' in element['ancestors']
        actionable = clickable or scrollable or long_clickable or editable
        
        # checked = self.__safe_dict_get(view, 'checked')
        selected = element['selected']
        content_description = element['content_desc']
        view_text = element['text']
        text_hint = element['text_hint']
        grid_location = element['grid_location']
        # focused = element['focused']  # focusable only reflects users' experience.

        # if the view is meaningless or can not be actioned, update the target element index
        if not content_description and not view_text and not text_hint and not scrollable:  # actionable?
            # if elementid < original_target_element_id:
            #     target_element_id -= 1
            # if elementid == original_target_element_id:
            #     print('########################### warning: the target element can never be touched #####################################')
            continue
        # if not actionable:
        #     if elementid < original_target_element_id:
        #         target_element_id -= 1
        #     if elementid == original_target_element_id:
        #         print('########################### warning: the target element can never be touched #####################################')
        
        view_status = ''
        if editable:
            view_status += 'editable '
        if selected:
            view_status += 'checked '
        view_desc = f'- a {view_status}view'

        if grid_location:
            view_desc = view_desc + ' at ' + grid_location.lower()

        if content_description:
            content_description = content_description.replace('\n', '  ')
            content_description = f'{content_description[:40]}...' if len(content_description) > 40 else content_description
            view_desc += f' "{content_description}"'
        if view_text:
            view_text = view_text.replace('\n', '  ')
            view_text = f'{view_text[:40]}...' if len(view_text) > 40 else view_text
            view_desc += f' with text "{view_text}"'
        if text_hint:
            text_hint = text_hint.replace('\n', '  ')
            text_hint = f'{text_hint[:40]}...' if len(text_hint) > 40 else text_hint
            text_hint += f' with text hint "{text_hint}"'

        if actionable:
            view_actions = []
            if editable:
                view_actions.append(f'edit ({len(available_actions)})')  # ({len(available_actions)}) is to get the index of the action to choose from
                available_actions.append('edit')
            if clickable:
                view_actions.append(f'click ({len(available_actions)})')
                available_actions.append('click')
            # if checkable:
            #     view_actions.append(f'check/uncheck ({len(available_actions)})')
            #     available_actions.append(TouchEvent(view=view))
            # if long_clickable:
            #     view_actions.append(f'long click ({len(available_actions)})')
            #     available_actions.append(LongTouchEvent(view=view))
            if scrollable:  # TODO: can judge here whether it is on the top(bottom) of the interface, meaning it can not scroll up(down)
                view_actions.append(f'scroll up ({len(available_actions)})')
                available_actions.append('scroll up')
                view_actions.append(f'scroll down ({len(available_actions)})')
                available_actions.append('scroll down')
            view_actions_str = ', '.join(view_actions)
            view_desc += f' that can {view_actions_str}'
        view_descs.append(view_desc)
    return view_descs

def get_described_actions(view_discription, target_element_id, last_view_discs=None, include_image_contents=False):
    """
    Get a text description of current state
    TODO: if include_image_contents, we describe the image element utilizing a multi-modal model 
    """
    # enabled_view_ids = []
    # for id, node in leafnode_discreption.items():
    #     # exclude navigation bar if exists
    #     if self.__safe_dict_get(view_dict, 'visible') and \
    #         self.__safe_dict_get(view_dict, 'resource_id') not in \
    #         ['android:id/navigationBarBackground',
    #         'android:id/statusBarBackground']: 
    #         enabled_view_ids.append(view_dict['temp_id'])
    available_actions = []
    view_descs = []
    actionable_views = []
    original_target_element_id = target_element_id
    for elementid, element in view_discription.items():
        clickable = element['clickable']
        scrollable = element['scrollable']
        # checkable = self._get_self_ancestors_property(view, 'checkable')
        long_clickable = element['long_clickable']
        editable = 'android.widget.EditText' in element['ancestors']
        actionable = clickable or scrollable or long_clickable or editable
        
        # checked = self.__safe_dict_get(view, 'checked')
        selected = element['selected']
        content_description = element['content_desc']
        view_text = element['text']
        text_hint = element['text_hint']
        grid_location = element['grid_location']
        # focused = element['focused']  # focusable only reflects users' experience.

        # if the view is meaningless or can not be actioned, update the target element index
        if not content_description and not view_text and not text_hint and not scrollable:  # actionable?
            if elementid < original_target_element_id:
                target_element_id -= 1
            if elementid == original_target_element_id:
                print('########################### warning: the target element can never be touched #####################################')
            continue
        if not actionable:
            if elementid < original_target_element_id:
                target_element_id -= 1
            if elementid == original_target_element_id:
                print('########################### warning: the target element can never be touched #####################################')
        
        view_status = ''
        if editable:
            view_status += 'editable '
        if selected:
            view_status += 'checked '
        view_desc = f'- a {view_status}view'

        if grid_location:
            view_desc = view_desc + ' at ' + grid_location.lower()

        if content_description:
            content_description = content_description.replace('\n', '  ')
            content_description = f'{content_description[:40]}...' if len(content_description) > 40 else content_description
            view_desc += f' "{content_description}"'
        if view_text:
            view_text = view_text.replace('\n', '  ')
            view_text = f'{view_text[:40]}...' if len(view_text) > 40 else view_text
            view_desc += f' with text "{view_text}"'
        if text_hint:
            text_hint = text_hint.replace('\n', '  ')
            text_hint = f'{text_hint[:40]}...' if len(text_hint) > 40 else text_hint
            text_hint += f' with text hint "{text_hint}"'
        

        if actionable:

            actionable_views.append(view_desc[2:])

            view_actions = []
            if editable:
                view_actions.append(f'edit ({len(available_actions)})')  # ({len(available_actions)}) is to get the index of the action to choose from
                available_actions.append('edit')
            if clickable:
                view_actions.append(f'click ({len(available_actions)})')
                available_actions.append('click')
            # if checkable:
            #     view_actions.append(f'check/uncheck ({len(available_actions)})')
            #     available_actions.append(TouchEvent(view=view))
            # if long_clickable:
            #     view_actions.append(f'long click ({len(available_actions)})')
            #     available_actions.append(LongTouchEvent(view=view))
            if scrollable:  # TODO: can judge here whether it is on the top(bottom) of the interface, meaning it can not scroll up(down)
                view_actions.append(f'scroll up ({len(available_actions)})')
                available_actions.append('scroll up')
                view_actions.append(f'scroll down ({len(available_actions)})')
                available_actions.append('scroll down')
            view_actions_str = ', '.join(view_actions)
            view_desc += f' that can {view_actions_str}'
            
        view_descs.append(view_desc)
    # old_view_descs = copy.deepcopy(view_descs)
    # import pdb;pdb.set_trace()
    if last_view_discs is not None and len(last_view_discs) <= len(view_descs):
        # all_equal = True
        not_equal = 0
        for discid in range(len(last_view_discs)):
            if last_view_discs[discid] != view_descs[discid]:
                print(last_view_discs[discid], view_descs[discid])
                # all_equal = False
                not_equal += 1
                # break
        if not_equal / len(last_view_discs) <= 0.1 and len(last_view_discs) / len(view_descs) <= 0.8:
            view_descs = view_descs[len(last_view_discs):]
    

    view_descs.append(f'- a key to go back ({len(available_actions)})')
    available_actions.append('go back')
    state_desc = 'The current state has the following UI views and corresponding actions, with action id in parentheses:\n '
    state_desc += ';\n '.join(view_descs)

    # old_state_desc = 'The current state has the following UI views and corresponding actions, with action id in parentheses:\n '
    # old_state_desc += ';\n '.join(old_view_descs)

    # import pdb;pdb.set_trace()
    # if last_view_disc is not None and last_view_disc in state_desc:
    #     # from difflib import Differ
    #     # d=Differ()
    #     # diff = d.compare(state_desc[:len(last_view_disc)], last_view_disc)
    #     # print(diff)
    #     state_desc = state_desc[len(last_view_disc):]
    #     state_desc = 'The current state has the following UI views and corresponding actions, with action id in parentheses:\n ' + state_desc

    return state_desc, available_actions, target_element_id, actionable_views

def get_view_desc(view):  # used when we query the llm to genertate the input
    content_description = view['content_desc']
    view_text = view['text']
    scrollable = view['scorallable']
    text_hint = view['text_hint']
    view_desc = f'view'
    if scrollable:
        view_desc = f'scrollable view'
    if content_description:
        view_desc += f' "{content_description}"'
    if view_text:
        view_text = view_text.replace('\n', '  ')
        view_text = f'{view_text[:40]}...' if len(view_text) > 40 else view_text
        view_desc += f' with text "{view_text}"'
    if text_hint:
        text_hint = text_hint.replace('\n', '  ')
        text_hint = f'{text_hint[:40]}...' if len(text_hint) > 40 else text_hint
        view_desc += f' with text hint "{text_hint}"'
    return view_desc

def get_action_desc(action, target_icon=None, text_input=None):  
    # as there are only three types of actions in motif, 
    # namely click, type, and swipe, we have to translate 'scroll' to 'swipe'

    # desc = action.event_type
    if action == 'go back':
        desc = f'- go back'
    else:  # This class describes a UI event of app, such as touch, click, etc
        action_name = action

        if text_input is not None:
            action_name = f'enter "{text_input}" into'
        if target_icon is not None:
            desc = f'- {action_name} {target_icon}'
        else:
            desc = f'- {action_name}'
    return desc

def get_whole_desc(task, state_prompt, history, is_edit=False, selected_view=None):  # Suppose you are quite familiar with the application {self.app}, which 
    task_prompt = f"I am using a smartphone to {task}."
    history_prompt = f'I have already completed the following steps, which should not be performed again: \n ' + ';\n '.join(history)
    question = 'Which action should I choose next? Just return the action id and nothing else.\nIf no more action is needed, return -1.'
    prompt = f'{task_prompt}\n{state_prompt}\n{history_prompt}\n{question}'
    if not is_edit:
        print(prompt)
        return prompt
    question = f'What text should I enter to the {selected_view}? Just return the text and nothing else.'
    prompt = f'{task_prompt}\n{state_prompt}\n{question}'
    print(prompt)
    return prompt


class LLMagent:
    def __init__(self, task, app):
        self.task = task
        self.app = app
        self.history = [f'- start the app {self.app}']
    
    def _query_llm(self, prompt):
        import requests
        URL = 'https://gpt.yanghuan.site/api/chat-stream'# os.environ['GPT_URL']  # NOTE: replace with your own GPT API
        body = {"model":"gpt-3.5-turbo","messages":[{"role":"user","content":prompt}],"stream":True}
        headers = {'Content-Type': 'application/json', 'path': 'v1/chat/completions'}
        r = requests.post(url=URL, json=body, headers=headers)
        return r.content.decode()

    def get_action_with_LLM(self, state_prompt, actionable_view_list, candidate_actions):  # Suppose you are quite familiar with the application {self.app}, which 
        task_prompt = f"I am using a smartphone to {self.task}."
        history_prompt = f'I have already completed the following steps, which should not be performed again: \n ' + ';\n '.join(self.history)
        question = 'Which action should I choose next? Just return the action id and nothing else.\nIf no more action is needed, return -1.'
        prompt = f'{task_prompt}\n{state_prompt}\n{history_prompt}\n{question}'
        print(prompt)
        response = self._query_llm(prompt)
        print(f'response: {response}')
        if '-1' in response:
            input(f"Seems the task is completed. Press Enter to continue...")
            return None, candidate_actions, 'finised'
        match = re.search(r'\d+', response)
        if not match:
            return None, candidate_actions, None
        idx = int(match.group(0))
        selected_action = candidate_actions[idx]
        selected_view = actionable_view_list[idx]
        
        if selected_action == 'edit':
            # view_text = get_view_desc(view)
            question = f'What text should I enter to the {selected_view}? Just return the text and nothing else.'
            prompt = f'{task_prompt}\n{state_prompt}\n{question}'
            print(prompt)
            response = self._query_llm(prompt)
            print(f'response: {response}')
            input_text = response.replace('"', '').replace(' ', '-')
            if len(input_text) > 30:  # heuristically disable long text input
                input_text = ''
            selected_action = 'edit ' + input_text
            action_desc = get_action_desc(selected_action, selected_view, input_text)
        else:
            action_desc = get_action_desc(selected_action, selected_view)

        self.update_action_history(action_desc)

        return selected_action, candidate_actions, action_desc
    
    def update_action_history(self, action):
        self.history.append(action)
    
    # def generate_event_based_on_utg(self):
    #     """
    #     generate an event based on current UTG
    #     @return: InputEvent
    #     """
    #     current_state = self.current_state
    #     self.logger.info("Current state: %s" % current_state.state_str)
    #     if current_state.state_str in self.__missed_states:
    #         self.__missed_states.remove(current_state.state_str)

    #     if current_state.get_app_activity_depth(self.app) < 0:
    #         # If the app is not in the activity stack
    #         start_app_intent = self.app.get_start_intent()

    #         # It seems the app stucks at some state, has been
    #         # 1) force stopped (START, STOP)
    #         #    just start the app again by increasing self.__num_restarts
    #         # 2) started at least once and cannot be started (START)
    #         #    pass to let viewclient deal with this case
    #         # 3) nothing
    #         #    a normal start. clear self.__num_restarts.

    #         if self.__event_trace.endswith(EVENT_FLAG_START_APP + EVENT_FLAG_STOP_APP) \
    #                 or self.__event_trace.endswith(EVENT_FLAG_START_APP):
    #             self.__num_restarts += 1
    #             self.logger.info("The app had been restarted %d times.", self.__num_restarts)
    #         else:
    #             self.__num_restarts = 0

    #         # pass (START) through
    #         if not self.__event_trace.endswith(EVENT_FLAG_START_APP):
    #             if self.__num_restarts > MAX_NUM_RESTARTS:
    #                 # If the app had been restarted too many times, enter random mode
    #                 msg = "The app had been restarted too many times. Entering random mode."
    #                 self.logger.info(msg)
    #                 self.__random_explore = True
    #             else:
    #                 # Start the app
    #                 self.__event_trace += EVENT_FLAG_START_APP
    #                 self.logger.info("Trying to start the app...")
    #                 self.__action_history = [f'- start the app {self.app.app_name}']
    #                 return IntentEvent(intent=start_app_intent)

    #     elif current_state.get_app_activity_depth(self.app) > 0:
    #         # If the app is in activity stack but is not in foreground
    #         self.__num_steps_outside += 1

    #         if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE:
    #             # If the app has not been in foreground for too long, try to go back
    #             if self.__num_steps_outside > MAX_NUM_STEPS_OUTSIDE_KILL:
    #                 stop_app_intent = self.app.get_stop_intent()
    #                 go_back_event = IntentEvent(stop_app_intent)
    #             else:
    #                 go_back_event = KeyEvent(name="BACK")
    #             self.__event_trace += EVENT_FLAG_NAVIGATE
    #             self.logger.info("Going back to the app...")
    #             self.__action_history.append('- go back')
    #             return go_back_event
    #     else:
    #         # If the app is in foreground
    #         self.__num_steps_outside = 0

    #     action, candidate_actions = self._get_action_with_LLM(current_state, self.__action_history)
    #     if action is not None:
    #         self.__action_history.append(current_state.get_action_desc(action))
    #         return action

    #     if self.__random_explore:
    #         self.logger.info("Trying random event.")
    #         action = random.choice(candidate_actions)
    #         self.__action_history.append(current_state.get_action_desc(action))
    #         return action

    #     # If couldn't find a exploration target, stop the app
    #     stop_app_intent = self.app.get_stop_intent()
    #     self.logger.info("Cannot find an exploration target. Trying to restart app...")
    #     self.__action_history.append('- stop the app')
    #     self.__event_trace += EVENT_FLAG_STOP_APP
    #     return IntentEvent(intent=stop_app_intent)