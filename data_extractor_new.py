import os
import glob
import json
import common
import prompt_generator
ENV_DIR = "output"
ROOT = '../motif_all_raw_data'  # '../data/motif/raw/traces_02_14_21'
PROCESSED_INFO = '../processed_motif_deduped/'

# TODO: allow model to randomly explore when it can not decide; how to cut if the prompt is too long

def ui_obj_to_str(ui_obj):
    # creates id by concatenating
    # different UI element fields
    ui_str_id = []

    ui_str_id += str(ui_obj.obj_type)
    ui_str_id += str(ui_obj.text)
    ui_str_id += str(ui_obj.resource_id)
    ui_str_id += str(ui_obj.android_class)
    ui_str_id += str(ui_obj.android_package)
    ui_str_id += str(ui_obj.content_desc)
    ui_str_id += str(ui_obj.clickable)
    ui_str_id += str(ui_obj.visible)
    ui_str_id += str(ui_obj.enabled)
    ui_str_id += str(ui_obj.focusable)
    ui_str_id += str(ui_obj.focused)
    ui_str_id += str(ui_obj.scrollable)
    ui_str_id += str(ui_obj.long_clickable)
    ui_str_id += str(ui_obj.selected)

    return " ".join(ui_str_id)

def get_uid(view_path, vh_w, vh_h):
    # get unique id for state in state-action graph
    # consists of concat str values from leaf nodes
    view_hierarchy_leaf_nodes = common.get_view_hierarchy_list(view_path, vh_w, vh_h)
    ui_objs = [ele.uiobject for ele in view_hierarchy_leaf_nodes]
    ui_objs_str = [ui_obj_to_str(ui) for ui in ui_objs]
    return " ".join(ui_objs_str)

def extract_view_hierarchy(view_leafnodes):
    leafnode_discreption = {}
    nodeidx = 0
    for leafnode in view_leafnodes:
        node_attrs = {'type': leafnode.uiobject.obj_type.name, 'name': leafnode.uiobject.obj_name, 
                      'clickable': leafnode.uiobject.clickable, 'enabled': leafnode.uiobject.enabled,
                      'scrollable': leafnode.uiobject.scrollable, 'long_clickable': leafnode.uiobject.long_clickable,
                      'selected': leafnode.uiobject.selected, 'text': leafnode.uiobject.text, 'content_desc': leafnode.uiobject.content_desc,
                      'word_sequence': leafnode.uiobject.word_sequence, 'grid_location': leafnode.uiobject.grid_location.name,
                      'focused': leafnode.uiobject.focused, 'focusable': leafnode.uiobject.focusable,
                      'ancestors': leafnode.uiobject.ancestors, 'text_hint': leafnode.uiobject.text_hint}
        leafnode_discreption[nodeidx] = node_attrs
        nodeidx += 1
    return leafnode_discreption

def is_view_useless(view):
    if not view['content_desc'] and not view['text'] and not view['text_hint'] and not view['scrollable']:
        return True
    else:
        return False


def extract_features(app):
    all_traces = glob.glob(os.path.join(ROOT, app, '*'))
    valid_image_number, invalid_image_number = 0, 0

    dataset = []

    for trace_path in all_traces:
        # import pdb;pdb.set_trace()
        trace_id = trace_path.split('/')[3]
        # print(trace_path)

        # os.mkdir(f'output/{app}/{trace_id}')

        try:
            with open(os.path.join(PROCESSED_INFO, trace_id + '.json')) as f:
                trace_info = json.load(f)
        except:
            continue

        last_view_description = None
        # agent = prompt_generator.LLMagent(task='tap news category settings item at the top right corner', app=trace_info["app"])

        action_history = [f'- start the app {app}']

        for imageidx in range(len(trace_info['images'])):
            current_view = trace_info['images'][imageidx]
            current_view_path = os.path.join(trace_path, 'view_hierarchies', current_view) + '.jpg'
            current_view_leafnodes = common.get_view_hierarchy_list(
                current_view_path, trace_info['vh_w'], trace_info['vh_h'])
            current_node_des = extract_view_hierarchy(current_view_leafnodes)
            # import pdb;pdb.set_trace()
            current_view_desc_from_original = prompt_generator.get_described_actions_from_original_view(current_node_des)

            if imageidx >= len(trace_info['ui_target_idxs']):  # this is the last image in the trace
                target_element_idx = -1
                view_description, available_actions, target_element_idx, actionable_views = \
                   prompt_generator.get_described_actions(current_node_des, target_element_idx, last_view_discs=last_view_description)
                
                if actionable_views == 'useless':
                    break

                prompt = prompt_generator.get_whole_desc(task=trace_info['goal'], state_prompt=view_description,\
                                                          history=action_history, is_edit=False)
            else:

                if trace_info['ui_target_idxs'][imageidx] != trace_info['ui_target_idxs_before'][imageidx] or trace_info['ui_target_idxs'][imageidx] == -1:
                    invalid_image_number += 1
                    last_view_description = current_view_desc_from_original
                    continue

                # get the target element the action should be executed on
                target_element_idx = trace_info['ui_target_idxs'][imageidx]
                # print(current_view_path, imageidx, current_node_des)

                if target_element_idx not in current_node_des.keys():
                    continue

                target_element = current_node_des[target_element_idx]
                # if the target element does not have any description, use the man-labelled description
                # if target_element['content_desc'] is None:
                #     target_element['content_desc'] = trace_info['obj_desc_str'][imageidx]
                if is_view_useless(target_element):
                    #print('view useless, skip it', current_view_path, imageidx)
                    invalid_image_number += 1
                    last_view_description = current_view_desc_from_original
                    continue
                view_description, available_actions, target_element_idx, actionable_views = \
                    prompt_generator.get_described_actions(current_node_des, target_element_idx, last_view_discs=last_view_description)
                
                if actionable_views == 'useless':
                    continue

                '''if trace_info['input_str'][imageidx] == "":
                    prompt = prompt_generator.get_whole_desc(task=trace_info['goal'], state_prompt=view_description, \
                                                             history=action_history, is_edit=False, instruction=trace_info["instr"][imageidx])
                    #action_history = prompt_generator.update_history(action_history, available_actions, target_element_idx, actionable_views)
                
                else:  # TODO: delete the input text if it already exits !!@@@
                    prompt_edit = prompt_generator.get_whole_desc(task=trace_info['goal'], state_prompt=view_description, history=action_history, \
                                                            is_edit=False, instruction=trace_info["instr"][imageidx])
                    
                    #action_history = prompt_generator.update_history(action_history, available_actions, target_element_idx, actionable_views)
                    prompt_content = prompt_generator.get_whole_desc(task=trace_info['goal'], state_prompt=view_description, history=action_history, \
                                                            is_edit=True, selected_view=actionable_views[target_element_idx], instruction=trace_info["instr"][imageidx])
                    #action_history = prompt_generator.update_history(action_history, available_actions, target_element_idx, actionable_views, text_input=trace_info['input_str'][imageidx])
                    if trace_info['input_str'][imageidx] in prompt_edit:
                        prompt_edit.replace(trace_info['input_str'][imageidx], '')
                    if trace_info['input_str'][imageidx] in prompt_content:
                        prompt_content.replace(trace_info['input_str'][imageidx], '')'''
                
                # if action_history == None:
                #     import pdb;pdb.set_trace()
            # import pdb;pdb.set_trace()


            valid_image_number += 1
            
            
            # print(target_element_idx, prompt)

            last_view_description = current_view_desc_from_original

            if imageidx >= len(trace_info['ui_target_idxs']) or trace_info['input_str'][imageidx] == "":
                # prompt_save_path  = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_prompt.json')
                # action_label_save_path  = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_action.json')
                # with open(prompt_save_path, 'w') as f:
                #     json.dump(prompt, f)
                
                # with open(action_label_save_path, 'w') as f:
                #     json.dump(target_element_idx, f)
                data_pair = {'instruction': '', 'input': prompt, 'output': str(target_element_idx)}
                dataset.append(data_pair)
            '''else:
                # prompt_save_path = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_prompt.json')
                # action_label_save_path  = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_action.json')
                # with open(prompt_save_path, 'w') as f:
                #     json.dump(prompt_edit, f)
                #     json.dump(prompt_content, f)
                
                # with open(action_label_save_path, 'w') as f:
                #     json.dump(target_element_idx, f)
                #     json.dump(trace_info['input_str'][imageidx], f)
                data_pair1 = {'instruction': '', 'input': prompt_edit, 'output': str(target_element_idx)}
                data_pair2 = {'instruction': '', 'input': prompt_content, 'output': trace_info['input_str'][imageidx]}
                dataset += [data_pair1, data_pair2]'''

            # if imageidx >= len(trace_info['ui_target_idxs']) or trace_info['input_str'][imageidx] == "":
            #     prompt_save_path  = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_prompt.json')
            #     action_label_save_path  = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_action.json')
            #     with open(prompt_save_path, 'w') as f:
            #         json.dump(prompt, f)
                
            #     with open(action_label_save_path, 'w') as f:
            #         json.dump(target_element_idx, f)
            # else:
            #     prompt_save_path = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_prompt.json')
            #     action_label_save_path  = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_action.json')
            #     with open(prompt_save_path, 'w') as f:
            #         json.dump(prompt_edit, f)
            #         json.dump(prompt_content, f)
                
            #     with open(action_label_save_path, 'w') as f:
            #         json.dump(target_element_idx, f)
            #         json.dump(trace_info['input_str'][imageidx], f)

    
    return dataset, valid_image_number, invalid_image_number
            
            # for i in current_view_leafnodes:
            #     print(i.uiobject.clickable, i.uiobject.obj_name)
            # for k, v in current_node_dis.items():
            #     print(k, v)
            
            # import pdb;pdb.set_trace()
    

def evaluate(app):
    all_traces = glob.glob(os.path.join(ROOT, app, '*'))
    for trace_path in all_traces:
        trace_id = trace_path.split('/')[6]
        # print(trace_path)

        # os.mkdir(f'output/{app}/{trace_id}')

        try:
            with open(os.path.join(PROCESSED_INFO, trace_id + '.json')) as f:
                trace_info = json.load(f)
        except:
            continue

        last_view_description = None

        agent = prompt_generator.LLMagent(task='tap news category settings item at the top right corner', app=trace_info["app"])

        action_history = [f'- start the app {app}']

        for imageidx in range(len(trace_info['images'])-1):
            current_view = trace_info['images'][imageidx]
            current_view_path = os.path.join(trace_path, 'view_hierarchies', current_view) + '.jpg'
            current_view_leafnodes = common.get_view_hierarchy_list(
                current_view_path, trace_info['vh_w'], trace_info['vh_h'])
            current_node_dis = extract_view_hierarchy(current_view_leafnodes)

            current_view_desc_from_original = prompt_generator.get_described_actions_from_original_view(current_node_dis)

            # get the target element the action should be executed on
            target_element = current_node_dis[trace_info['ui_target_idxs'][imageidx]]
            
            if target_element['content_desc'] is None:
                target_element['content_desc'] = trace_info['obj_desc_str'][imageidx]

            
            
            view_description, available_actions, target_element_id, actionable_views = \
                  prompt_generator.get_described_actions(current_node_dis, trace_info['ui_target_idxs'][imageidx], last_view_discs=last_view_description)
            
            selected_action, candidate_actions, action_desc = agent.get_action_with_LLM( \
                view_description, actionable_views, available_actions, )
            
            if action_desc is None:
                for _ in range(5):
                    print('warning: response not correct, trying again ...')
                    selected_action, candidate_actions, action_desc = agent.get_action_with_LLM( \
                            view_description, actionable_views, available_actions, )
                    if action_desc is not None:
                        break
            
            print(target_element_id, current_view_path)

            # import pdb;pdb.set_trace()
            last_view_description = current_view_desc_from_original

            # prompt_save_path  = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_prompt.json')
            # action_label_save_path  = os.path.join(f'output/{app}/{trace_id}', f'{current_view}_action.json')
            # with open(prompt_save_path, 'w') as f:
            #     json.dump(trace_feature, f)
            
            # with open(action_label_save_path, 'w') as f:
            #     json.dump(trace_feature, f)
            
            # for i in current_view_leafnodes:
            #     print(i.uiobject.clickable, i.uiobject.obj_name)
            # for k, v in current_node_dis.items():
            #     print(k, v)
            
            # import pdb;pdb.set_trace()



if __name__ == "__main__":
    if not os.path.isdir(ENV_DIR):
        os.mkdir(ENV_DIR)
   
    test_apps = [x.split('/')[-1] for x in glob.glob('../motif_all_raw_data/*')]
    i = 0
    apps = test_apps
    print('%d many apps to create test time graphs for' % len(test_apps))

    datapairs = []

    # apps = ['com.google.android.music']

    valid_images_total, invalid_images_total = 0, 0
    for app in apps:
        print((app, i))
        # os.mkdir(f'output/{app}')
        i += 1
        
        app_dataset, valid, invalid = extract_features(app)
        print(app_dataset, valid, invalid)
        datapairs += app_dataset

        valid_images_total += valid
        invalid_images_total += invalid
        # save_graph_path = os.path.join(ENV_DIR, app + '_graph.json')
        # save_map_path = os.path.join(ENV_DIR, app + '_feature.json')
        
    with open('motif_llama7.json', 'w') as f:
        json.dump(datapairs, f)
    
    #import pdb;pdb.set_trace()
    
    
    print(valid_images_total, invalid_images_total)