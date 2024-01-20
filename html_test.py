import copy
import math
import os
import json
from treelib import Tree
class DeviceState(object):
    def __init__(self, views):
        self.views = self.__parse_views(views)
        self.view_tree = {}
        self.__assemble_view_tree(self.view_tree, self.views)
        self.possible_events = None

    def __parse_views(self, raw_views):
        views={}
        if not raw_views or len(raw_views) == 0:
            return views

        for (key,value) in raw_views.items():
            # # Simplify resource_id
            # resource_id = view_dict['resource_id']
            # if resource_id is not None and ":" in resource_id:
            #     resource_id = resource_id[(resource_id.find(":") + 1):]
            #     view_dict['resource_id'] = resource_id
            views[key]=value
        return views

    def __assemble_view_tree(self, root_view, views):
        if not len(self.view_tree):  # bootstrap
            self.view_tree = copy.deepcopy(views["children"])
            self.__assemble_view_tree(self.view_tree, views)
        else:
            children = list(enumerate(root_view["children"]))
            print(children)
            if not len(children):
                return
            for i, j in children:
                root_view["children"][i] = copy.deepcopy(self.views[j])
                self.__assemble_view_tree(root_view["children"][i], views)


    @staticmethod
    def __safe_dict_get(view_dict, key, default=None):
        return_itm = view_dict[key] if (key in view_dict) else default
        if return_itm == None:
            return_itm = ''
        return return_itm

    def _get_self_ancestors_property(self, view, key, default=None):
        all_views = [view] + [self.views[i] for i in self.get_all_ancestors(view)]
        for v in all_views:
            value = self.__safe_dict_get(v, key)
            if value:
                return value
        return default

    def _remove_view_ids(self, views):
        removed_views = []
        for view_desc in views:
            if view_desc[0] == ' ':
                view_desc = view_desc[1:]
            view_desc_list = view_desc.split(' ', 2)
            if len(view_desc_list) > 2:
                removed_views.append(view_desc_list[0] + ' ' + view_desc_list[2])
            else:  # for example, <p id=4>June</p>
                latter_part = view_desc_list[1].split('>', 1)
                view_without_id = view_desc_list[0] + '>' + latter_part[1]
                # print('************', view_desc, view_without_id)
                removed_views.append(view_without_id)
        return removed_views

    def get_number_free_screen(self, prefix=''):
        """
        Get a text description of current state
        """

        enabled_view_ids = []
        for view_dict in self.views:
            # exclude navigation bar if exists
            if self.__safe_dict_get(view_dict, 'visible') and \
                    self.__safe_dict_get(view_dict, 'resource_id') not in \
                    ['android:id/navigationBarBackground',
                     'android:id/statusBarBackground']:
                enabled_view_ids.append(view_dict['temp_id'])

        text_frame = "<p id=@ class='&'>#</p>"
        btn_frame = "<button id=@ class='&' checked=$>#</button>"
        input_frame = "<input id=@ class='&' >#</input>"
        scroll_down_frame = "<div id=@ class='scroller'>scroll down</div>"
        scroll_up_frame = "<div id=@ class='scroller'>scroll up</div>"

        view_descs = []
        for view_id in enabled_view_ids:
            view = self.views[view_id]
            clickable = self.__safe_dict_get(view, 'clickable')
            scrollable = self.__safe_dict_get(view, 'scrollable')
            checkable = self.__safe_dict_get(view, 'checkable')
            long_clickable = self.__safe_dict_get(view, 'long_clickable')
            editable = self.__safe_dict_get(view, 'editable')
            actionable = clickable or scrollable or checkable or long_clickable or editable
            checked = self.__safe_dict_get(view, 'checked', default=False)
            selected = self.__safe_dict_get(view, 'selected', default=False)
            content_description = self.__safe_dict_get(view, 'content_desc', default='')
            view_text = self.__safe_dict_get(view, 'text', default='')
            view_class = self.__safe_dict_get(view, 'class').split('.')[-1]
            if not content_description and not view_text and not scrollable:  # actionable?
                continue

            #content_description = self._remove_date_and_date(content_description)
            #view_text = self._remove_date_and_date(view_text)
            # text = self._merge_text(view_text, content_description)
            # view_status = ''
            if editable:
                # view_status += 'editable '
                view_desc = input_frame.replace('@', str(len(view_descs))).replace('#', view_text)
                if content_description:
                    view_desc = view_desc.replace('&', content_description)
                else:
                    view_desc = view_desc.replace(" text='&'", "")
                view_descs.append(view_desc)
            elif (clickable or checkable or long_clickable):

                view_desc = btn_frame.replace('@', str(len(view_descs))).replace('#', view_text).replace('$',
                                                                                                         str(checked or selected))
                # import pdb;pdb.set_trace()
                if content_description:
                    view_desc = view_desc.replace('&', content_description)
                else:
                    view_desc = view_desc.replace(" text='&'", "")
                view_descs.append(view_desc)
            elif scrollable:
                view_descs.append(
                    scroll_up_frame.replace('@', str(len(view_descs))))  # .replace('&', view_class).replace('#', text))
                view_descs.append(scroll_down_frame.replace('@', str(len(
                    view_descs))))  # .replace('&', view_class).replace('#', text))
            else:
                view_desc = text_frame.replace('@', str(len(view_descs))).replace('#', view_text)

                if content_description:
                    view_desc = view_desc.replace('&', content_description)
                else:
                    view_desc = view_desc.replace(" text='&'", "")
                view_descs.append(view_desc)
        view_descs.append(f"<button id={len(view_descs)} text='ImageButton'>go back</button>")
        # state_desc = 'The current state has the following UI elements: \n' #views and corresponding actions, with action id in parentheses:\n '
        state_desc = prefix  # 'Given a screen, an instruction, predict the id of the UI element to perform the insturction. The screen has the following UI elements: \n'
        # state_desc = 'You can perform actions on a contacts app, the current state of which has the following UI views and corresponding actions, with action id in parentheses:\n'
        state_desc += '\n '.join(view_descs)

        views_without_id = self._remove_view_ids(view_descs)

        return state_desc, views_without_id

def main():

    f = open('shuju.json', 'r',encoding='utf-8')
    content = f.read()
    view = json.loads(content)["activity"]
    f.close()
    #print(view["root"])
    mysample=DeviceState(view["root"])
    #print(mysample.view_tree)
    #print(mysample.views)
    state,views=mysample.get_number_free_screen()
    #print(views)

main()