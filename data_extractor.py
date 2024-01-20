import os
import glob
import json
import common
import prompt_generator
ENV_DIR = "output"
ROOT = '../data/motif/raw/traces_03_17_21'  # '../data/motif/raw/traces_02_14_21'
PROCESSED_INFO = '../data/motif/processed_motif_deduped/'

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


def extract_tasks(app):
    all_traces = glob.glob(os.path.join(ROOT, app, '*'))
    for trace_path in all_traces:
        trace_id = trace_path.split('/')[6]
        print(trace_path)

        # os.mkdir(f'output/{app}/{trace_id}')

        try:
            with open(os.path.join(PROCESSED_INFO, trace_id + '.json')) as f:
                trace_info = json.load(f)
        except:
            continue

        last_view_description = None

        agent = prompt_generator.LLMagent(task='tap news category settings item at the top right corner', app=trace_info["app"])


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
   
    test_apps = [x.split('/')[-1] for x in glob.glob('../data/motif/raw/traces_03_17_21/*')]
    i = 0
    apps = test_apps
    print('%d many apps to create test time graphs for' % len(test_apps))
    # apps = ['com.groupon']
    for app in apps:
        print((app, i))
        
        i += 1
        
        trace_feature = extract_tasks(app)
        # save_graph_path = os.path.join(ENV_DIR, app + '_graph.json')
        # save_map_path = os.path.join(ENV_DIR, app + '_feature.json')
        
        # with open(save_map_path, 'w') as f:
        #     json.dump(trace_feature, f)




        