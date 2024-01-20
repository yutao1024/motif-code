# coding=utf-8
# Copyright 2021 The Google Research Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Functions shared among files under word2act/data_generation."""

# from __future__ import absolute_import
# from __future__ import division
# from __future__ import print_function

import collections
import os
import json
import yaml
import attr
from enum import Enum
import numpy as np
import tensorflow._api.v2.compat.v1 as tf


import config
import view_hierarchy

tf.disable_v2_behavior()
gfile = tf.gfile


def get_screen_dims(views, trace_exceptions='widget_exception_dims.json'):
    with open(trace_exceptions) as f:
        widget_exceptions = json.load(f)

    trace = views[0].split('/')[-3]
    if trace in widget_exceptions:
        return [int(widget_exceptions[trace][0]), int(widget_exceptions[trace][1])]

    for view in views:
        with open(view, 'r') as f:
            data = json.load(f)
            bbox = data['activity']['root']['bounds']
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
        if bbox[0] == 0 and bbox[1] == 0:
            return width, height


@attr.s
class MaxValues(object):
  """Represents max values for a task and UI."""

  # For instrction
  max_word_num = attr.ib(default=None)
  max_word_length = attr.ib(default=None)

  # For UI objects
  max_ui_object_num = attr.ib(default=None)
  max_ui_object_word_num = attr.ib(default=None)
  max_ui_object_word_length = attr.ib(default=None)

  def update(self, other):
    """Update max value from another MaxValues instance.

    This will be used when want to merge several MaxValues instances:

      max_values_list = ...
      result = MaxValues()
      for v in max_values_list:
        result.update(v)

    Then `result` contains merged max values in each field.

    Args:
      other: another MaxValues instance, contains updated data.
    """
    self.max_word_num = max(self.max_word_num, other.max_word_num)
    self.max_word_length = max(self.max_word_length, other.max_word_length)
    self.max_ui_object_num = max(self.max_ui_object_num,
                                 other.max_ui_object_num)
    self.max_ui_object_word_num = max(self.max_ui_object_word_num,
                                      other.max_ui_object_word_num)
    self.max_ui_object_word_length = max(self.max_ui_object_word_length,
                                         other.max_ui_object_word_length)


class ActionRules(Enum):
  """The rule_id to generate synthetic action."""
  SINGLE_OBJECT_RULE = 0
  GRID_CONTEXT_RULE = 1
  NEIGHBOR_CONTEXT_RULE = 2
  SWIPE_TO_OBJECT_RULE = 3
  SWIPE_TO_DIRECTION_RULE = 4
  REAL = 5  # The action is not generated, but a real user action.
  CROWD_COMPUTE = 6
  DIRECTION_VERB_RULE = 7  # For win, "click button under some tab/combobox
  CONSUMED_MULTI_STEP = 8  # For win, if the target verb is not direction_verb
  UNCONSUMED_MULTI_STEP = 9
  NO_VERB_RULE = 10


class ActionTypes(Enum):
  """The action types and ids of Android actions."""
  CLICK = 2
  INPUT = 3
  SWIPE = 4
  CHECK = 5
  UNCHECK = 6
  LONG_CLICK = 7
  OTHERS = 8
  GO_HOME = 9
  GO_BACK = 10


VERB_ID_MAP = {
    'check': ActionTypes.CHECK,
    'find': ActionTypes.SWIPE,
    'navigate': ActionTypes.SWIPE,
    'uncheck': ActionTypes.UNCHECK,
    'head to': ActionTypes.SWIPE,
    'enable': ActionTypes.CHECK,
    'turn on': ActionTypes.CHECK,
    'locate': ActionTypes.SWIPE,
    'disable': ActionTypes.UNCHECK,
    'tap and hold': ActionTypes.LONG_CLICK,
    'long press': ActionTypes.LONG_CLICK,
    'look': ActionTypes.SWIPE,
    'press and hold': ActionTypes.LONG_CLICK,
    'turn it on': ActionTypes.CHECK,
    'turn off': ActionTypes.UNCHECK,
    'switch on': ActionTypes.CHECK,
    'visit': ActionTypes.SWIPE,
    'hold': ActionTypes.LONG_CLICK,
    'switch off': ActionTypes.UNCHECK,
    'head': ActionTypes.SWIPE,
    'head over': ActionTypes.SWIPE,
    'long-press': ActionTypes.LONG_CLICK,
    'un-click': ActionTypes.UNCHECK,
    'tap': ActionTypes.CLICK,
    'check off': ActionTypes.UNCHECK,
    # 'power on': 21
}


class WinActionTypes(Enum):
  """The action types and ids of windows actions."""
  LEFT_CLICK = 2
  RIGHT_CLICK = 3
  DOUBLE_CLICK = 4
  INPUT = 5


@attr.s
class Action(object):
  """The class for a word2act action."""
  instruction_str = attr.ib(default=None)
  verb_str = attr.ib(default=None)
  obj_desc_str = attr.ib(default=None)
  input_content_str = attr.ib(default=None)
  action_type = attr.ib(default=None)
  action_rule = attr.ib(default=None)
  target_obj_idx = attr.ib(default=None)
  obj_str_pos = attr.ib(default=None)
  input_str_pos = attr.ib(default=None)
  verb_str_pos = attr.ib(default=None)
  # start/end position of one whole step
  step_str_pos = attr.ib(default=[0, 0])
  # Defalt action is 1-step consumed action
  is_consumed = attr.ib(default=True)

  def __eq__(self, other):
    if not isinstance(other, Action):
      return NotImplemented
    return self.instruction_str == other.instruction_str

  def is_valid(self):
    """Does valid check for action instance.

    Returns true when any component is None or obj_desc_str is all spaces.

    Returns:
      a boolean
    """
    invalid_obj_pos = (np.array(self.obj_str_pos) == 0).all()
    if (not self.instruction_str or invalid_obj_pos or
        not self.obj_desc_str.strip()):
      return False

    return True

  def has_valid_input(self):
    """Does valid check for input positions.

    Returns true when input_str_pos is not all default value.

    Returns:
      a boolean
    """
    return (self.input_str_pos != np.array([
        config.LABEL_DEFAULT_VALUE_INT, config.LABEL_DEFAULT_VALUE_INT
    ])).any()

  def regularize_strs(self):
    """Trims action instance's obj_desc_str, input_content_str, verb_str."""
    self.obj_desc_str = self.obj_desc_str.strip()
    self.input_content_str = self.input_content_str.strip()
    self.verb_str = self.verb_str.strip()

  def convert_to_lower_case(self):
    self.instruction_str = self.instruction_str.lower()
    self.obj_desc_str = self.obj_desc_str.lower()
    self.input_content_str = self.input_content_str.lower()
    self.verb_str = self.verb_str.lower()


@attr.s
class ActionEvent(object):
  """This class defines ActionEvent class.

  ActionEvent is high level event summarized from low level android event logs.
  This example shows the android event logs and the extracted ActionEvent
  object:

  Android Event Logs:
  [      42.407808] EV_ABS       ABS_MT_TRACKING_ID   00000000
  [      42.407808] EV_ABS       ABS_MT_TOUCH_MAJOR   00000004
  [      42.407808] EV_ABS       ABS_MT_PRESSURE      00000081
  [      42.407808] EV_ABS       ABS_MT_POSITION_X    00004289
  [      42.407808] EV_ABS       ABS_MT_POSITION_Y    00007758
  [      42.407808] EV_SYN       SYN_REPORT           00000000
  [      42.453256] EV_ABS       ABS_MT_PRESSURE      00000000
  [      42.453256] EV_ABS       ABS_MT_TRACKING_ID   ffffffff
  [      42.453256] EV_SYN       SYN_REPORT           00000000

  This log can be generated from this command during runing android emulator:
  adb shell getevent -lt /dev/input/event1

  If screen pixel size is [480,800], this is the extracted ActionEvent Object:
    ActionEvent(
      event_time = 42.407808
      action_type = ActionTypes.CLICK
      action_object_id = -1
      coordinates_x = [17033,]
      coordinates_y = [30552,]
      coordinates_x_pixel = [249,]
      coordinates_y_pixel = [747,]
      action_params = []
    )
  """

  event_time = attr.ib()
  action_type = attr.ib()
  coordinates_x = attr.ib()
  coordinates_y = attr.ib()
  action_params = attr.ib()
  # These fields will be generated by public method update_info_from_screen()
  coordinates_x_pixel = None
  coordinates_y_pixel = None
  object_id = config.LABEL_DEFAULT_INVALID_INT
  leaf_nodes = None  # If dedup, the nodes here will be less than XML
  debug_target_object_word_sequence = None

  def update_info_from_screen(self, screen_info, dedup=False):
    """Updates action event attributes from screen_info.

    Updates coordinates_x(y)_pixel and object_id from the screen_info proto.

    Args:
      screen_info: ScreenInfo protobuf
      dedup: whether dedup the UI objs with same text or content desc.
    Raises:
      ValueError when fail to find object id.
    """
    self.update_norm_coordinates((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    vh = view_hierarchy.ViewHierarchy()
    vh.load_xml(screen_info.view_hierarchy.xml.encode('utf-8'))
    if dedup:
      vh.dedup((self.coordinates_x_pixel[0], self.coordinates_y_pixel[0]))
    self.leaf_nodes = vh.get_leaf_nodes()
    ui_object_list = vh.get_ui_objects()
    self._update_object_id(ui_object_list)

  def _update_object_id(self, ui_object_list):
    """Updates ui object index from view_hierarchy.

    If point(X,Y) surrounded by multiple UI objects, select the one with
    smallest area.

    Args:
      ui_object_list: .
    Raises:
      ValueError when fail to find object id.
    """
    smallest_area = -1
    for index, ui_obj in enumerate(ui_object_list):
      box = ui_obj.bounding_box
      if (box.x1 <= self.coordinates_x_pixel[0] <= box.x2 and
          box.y1 <= self.coordinates_y_pixel[0] <= box.y2):
        area = (box.x2 - box.x1) * (box.y2 - box.y1)
        if smallest_area == -1 or area < smallest_area:
          self.object_id = index
          self.debug_target_object_word_sequence = ui_obj.word_sequence
          smallest_area = area

    if smallest_area == -1:
      raise ValueError(('Object id not found: x,y=%d,%d coordinates fail to '
                        'match every UI bounding box') %
                       (self.coordinates_x_pixel[0],
                        self.coordinates_y_pixel[0]))

  def update_norm_coordinates(self, screen_size):
    """Update coordinates_x(y)_norm according to screen_size.

    self.coordinate_x is scaled between [0, ANDROID_LOG_MAX_ABS_X]
    self.coordinate_y is scaled between [0, ANDROID_LOG_MAX_ABS_Y]
    This function recovers coordinate of android event logs back to coordinate
    in real screen's pixel level.

    coordinates_x_pixel = coordinates_x/ANDROID_LOG_MAX_ABS_X*horizontal_pixel
    coordinates_y_pixel = coordinates_y/ANDROID_LOG_MAX_ABS_Y*vertical_pixel

    For example,
    ANDROID_LOG_MAX_ABS_X = ANDROID_LOG_MAX_ABS_Y = 32676
    coordinate_x = [17033, ]
    object_cords_y = [30552, ]
    screen_size = (480, 800)
    Then the updated pixel coordinates are as follow:
      coordinates_x_pixel = [250, ]
      coordinates_y_pixel = [747, ]

    Args:
      screen_size: a tuple of screen pixel size.
    """
    (horizontal_pixel, vertical_pixel) = screen_size
    self.coordinates_x_pixel = [
        int(cord * horizontal_pixel / config.ANDROID_LOG_MAX_ABS_X)
        for cord in self.coordinates_x
    ]
    self.coordinates_y_pixel = [
        int(cord * vertical_pixel / config.ANDROID_LOG_MAX_ABS_Y)
        for cord in self.coordinates_y
    ]


# For Debug: Get distribution info for each cases
word_num_distribution_dict = collections.defaultdict(int)
word_length_distribution_dict = collections.defaultdict(int)


def get_word_statistics(file_path, motif=True, screen_w=None, screen_h=None):
  """Calculates maximum word number/length from ui objects in one xml/json file.

  Args:
    file_path: The full path of a xml/json file.

  Returns:
    A tuple (max_word_num, max_word_length)
      ui_object_num: UI object num.
      max_word_num: The maximum number of words contained in all ui objects.
      max_word_length: The maximum length of words contained in all ui objects.
  """
  max_word_num = 0
  max_word_length = 0

  leaf_nodes = get_view_hierarchy_list(file_path, screen_w, screen_h)
  for view_hierarchy_object in leaf_nodes:
    word_sequence = view_hierarchy_object.uiobject.word_sequence
    word_sequence = list(word_sequence)
    max_word_num = max(max_word_num, len(word_sequence))
    word_num_distribution_dict[len(word_sequence)] += 1

    for word in word_sequence:
      max_word_length = max(max_word_length, len(word))
      word_length_distribution_dict[len(word)] += 1
  return len(leaf_nodes), max_word_num, max_word_length


def get_ui_max_values(file_paths):
  """Calculates max values from ui objects in multi xml/json files.

  Args:
    file_paths: The full paths of multi xml/json files.
  Returns:
    max_values: instrance of MaxValues.
  """
  max_values = MaxValues()
  for file_path in file_paths:
    (ui_object_num,
     max_ui_object_word_num,
     max_ui_object_word_length) = get_word_statistics(file_path)

    max_values.max_ui_object_num = max(
        max_values.max_ui_object_num, ui_object_num)
    max_values.max_ui_object_word_num = max(
        max_values.max_ui_object_word_num, max_ui_object_word_num)
    max_values.max_ui_object_word_length = max(
        max_values.max_ui_object_word_length, max_ui_object_word_length)
  return max_values


def get_ui_object_list(file_path):
  """Gets ui object list from view hierarchy leaf nodes.

  Args:
    file_path: file path of xml or json
  Returns:
    A list of ui objects according to view hierarchy leaf nodes.
  """
  vh = _get_view_hierarchy(file_path)
  return vh.get_ui_objects()


def get_view_hierarchy_list(file_path, MOTIF_SCREEN_WIDTH=0, MOTIF_SCREEN_HEIGHT=0):
  """Gets view hierarchy leaf node list.

  Args:
    file_path: file path of xml or json
  Returns:
    A list of view hierarchy leaf nodes.
  """
  vh = _get_view_hierarchy(file_path, MOTIF_SCREEN_WIDTH, MOTIF_SCREEN_HEIGHT)
  return vh.get_leaf_nodes()


def _get_view_hierarchy(file_path, MOTIF_SCREEN_WIDTH=0, MOTIF_SCREEN_HEIGHT=0):
  """Gets leaf nodes view hierarchy lists.

  Args:
    file_path: The full path of an input xml/json file.
  Returns:
    A ViewHierarchy object.
  Raises:
    ValueError: unsupported file format.
  """
  with gfile.GFile(file_path, 'r') as f:
    data = f.read()

  _, file_extension = os.path.splitext(file_path)
  if file_extension == '.xml':
    vh = view_hierarchy.ViewHierarchy(
        screen_width=config.SCREEN_WIDTH, screen_height=config.SCREEN_HEIGHT)
    vh.load_xml(data)
  elif file_extension == '.json':
    vh = view_hierarchy.ViewHierarchy(
        screen_width=config.RICO_SCREEN_WIDTH,
        screen_height=config.RICO_SCREEN_HEIGHT)
    vh.load_json(data)
  elif file_extension == '.jpg':
    vh = view_hierarchy.ViewHierarchy(
      screen_width=MOTIF_SCREEN_WIDTH,
      screen_height=MOTIF_SCREEN_HEIGHT)
    vh.load_json(data, file_path)
  else:
    raise ValueError('unsupported file format %s' % file_extension)
  return vh

def get_html(path,actions_file,name_str):
    view_list,actions_list,input_list,valid,task,app,actions,obj_desc=get_info(actions_file)
    html_list=[]
    if valid:
        for i in range(len(actions_list)):
            view_str,action_id=get_viewstr(path,view_list[i],actions_list[i])
            view_html = {'Choice':action_id, 'Input':input_list[i], 'State':view_str,'action':actions[i],'obj_desc':obj_desc[i]}
            html_list.append(view_html)
        view_str,action_id=get_viewstr(path,view_list[len(view_list)-1],-1)
        view_html = {'Choice':-1, 'Input':'', 'State':view_str}
        html_list.append(view_html)
        with open('../motif/'+name_str+'.yaml', 'w',encoding='utf-8') as f:
            data={'task':task,'app':app,'records':html_list}
            f.write(yaml.dump(data, allow_unicode=True, sort_keys=False))
                
def get_viewstr(path,view,actions):
    view_str = ""
    hierarchy_list = get_view_hierarchy_list(path+'/view_hierarchies/'+view+'.jpg',
                                                     1440, 2960)
    leaf_object_list = []
    for leaf in hierarchy_list:
        leaf_object_list.append(leaf.uiobject)
    views,action=get_number_free_screen(leaf_object_list,actions)
    for j in range(len(views)):
        view_str=view_str+views[j]+'\n'
    return view_str,action

def get_number_free_screen(views,actions_id):
    """
    Get a text description of current state
    """

    enabled_view = []
    for view_dict in views:
        # exclude navigation bar if exists
        if view_dict.visible and \
               view_dict.resource_id not in \
                ['android:id/navigationBarBackground',
                 'android:id/statusBarBackground']:
            enabled_view.append(view_dict)

    text_frame = "<p id=@ text='&'>#</p>"
    btn_frame = "<button id=@ text='&' title='$'>#</button>"
    input_frame = "<input id=@ text='&' title='$'>#</input>"
    scroll_down_frame = "<div id=@ text='scroller'>scroll down</div>"
    scroll_up_frame = "<div id=@ text='scroller'>scroll up</div>"
    checkbox_frame="<checkbox id=@ checked=$>#</checkbox>"

    view_descs = []
    for view in enabled_view:
        #uiclass=view.android_class
        clickable = view.clickable
        scrollable = view.scrollable
        long_clickable = view.long_clickable
        editable = 'android.widget.EditText' in view.ancestors
        selected=view.selected
        content_description = view.content_desc
        view_text = view.text
        text_hint=view.text_hint

        if not text_hint and not content_description and not view_text and not scrollable:  # actionable?
            if actions_id>len(view_descs):
                actions_id=actions_id-1
            continue
        # content_description = self._remove_date_and_date(content_description)
        # view_text = self._remove_date_and_date(view_text)
        # text = self._merge_text(view_text, content_description)
        # view_status = ''
        if editable:
            # view_status += 'editable '
            view_desc = input_frame.replace('@', str(len(view_descs))).replace('#', view_text)
            if content_description:
                view_desc = view_desc.replace('&', content_description)
            else:
                view_desc = view_desc.replace(" text='&'", "")
            if text_hint:
                view_desc = view_desc.replace('$', text_hint)
            else:
                view_desc = view_desc.replace(" title='$'", "")
            view_descs.append(view_desc)
        elif (clickable or long_clickable):
            if selected:
                view_desc = checkbox_frame.replace('@', str(len(view_descs))).replace('#', view_text).replace('$',"True")
            else:
                view_desc = btn_frame.replace('@', str(len(view_descs))).replace('#', view_text)
            # import pdb;pdb.set_trace()
                if content_description:
                    view_desc = view_desc.replace('&', content_description)
                else:
                    view_desc = view_desc.replace(" text='&'", "")
                if text_hint:
                    view_desc = view_desc.replace('$', text_hint)
                else:
                    view_desc = view_desc.replace(" title='$'", "")
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

    return view_descs,actions_id

def get_info(file_path):
    is_valid=True
    f = open(file_path, 'r', encoding='utf-8')
    info=json.loads(f.read())
    actions_list = info["ui_target_idxs"]
    input_str=info["input_str"]
    img_list=info["images"]
    goals=info["goal"]
    app=info["app"]
    actions=info["actions"]
    obj_desc=info["obj_desc_str"]
    for index in  range(len(info['ui_target_idxs'])):
        if info['ui_target_idxs'][index] != info['ui_target_idxs_before'][index] or info['ui_target_idxs'][index] == -1:
            is_valid=False
            break
    f.close()
    return img_list,actions_list,input_str,is_valid,goals,app,actions,obj_desc


if __name__ == "__main__":
    '''files=['D:\\专用\\f898141e-6496-4684-8efb-60c0ca75317f_110_1612310356066.jpg','D:\\专用\\f898141e-6496-4684-8efb-60c0ca75317f_116_1612310356971.jpg','D:\\专用\\f898141e-6496-4684-8efb-60c0ca75317f_122_1612310357840.jpg','D:\\专用\\f898141e-6496-4684-8efb-60c0ca75317f_130_1612310359693.jpg','D:\\专用\\f898141e-6496-4684-8efb-60c0ca75317f_139_1612310362090.jpg']
    actions_file='D:\\专用\\2c5adc56-cb66-4ae0-bd54-37343b9adca8.json'
    get_html(files, actions_file)'''
    for item in os.scandir('../motif_all_raw_data'):
        for file in os.scandir(item.path):
            files=[]
            actions_file='../processed_motif_deduped/'+file.name+'.json'
            if os.path.exists(actions_file) and os.path.exists(file.path+"/view_hierarchies"):
                get_html(file.path,actions_file,file.name)