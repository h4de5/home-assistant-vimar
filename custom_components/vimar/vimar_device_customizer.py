import logging
import sys
import re

DEVICE_OVERRIDE_FILTER = "filter"
DEVICE_OVERRIDE_FILTER_RE = "filter_re"
DEVICE_OVERRIDE_ACTIONS = "actions"
DEVICE_OVERRIDE_ACTION_FRIENDLY_NAME_AS_VIMAR = "friendly_name_as_vimar"
DEVICE_OVERRIDE_ACTION_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN = "friendly_name_room_name_at_begin"
DEVICE_OVERRIDE_ACTION_REPLACE_RE = "replace_re"
DEVICE_OVERRIDE_ACTION_REPLACE_RE_FIELD = "field"
DEVICE_OVERRIDE_ACTION_REPLACE_RE_PATTERN = "pattern"
DEVICE_OVERRIDE_ACTION_REPLACE_RE_REPL = "repl"

_LOGGER = logging.getLogger(__name__)
_LOGGER_isDebug = _LOGGER.isEnabledFor(logging.DEBUG)

class VimarDeviceCustomizer:

    _device_overrides = []

    def __init__(self, device_overrides):
        """Create new container to hold all states."""
        self._device_overrides = device_overrides
        if (device_overrides is None):
            self._device_overrides = []
        self.init_overrides()


    def init_overrides(self):
        for device_override in self._device_overrides:
            self.device_override_fix(device_override)


    def customize_device(self, device):
        deviceold = None
        for device_override in self._device_overrides:
            try:
                match = self.device_override_match(device, device_override)
                if not match:
                    continue
                if (deviceold is None and _LOGGER_isDebug):
                    deviceold = {}
                    for key, value in device.items():
                        deviceold[key] = self.device_override_get_attr_str(device, key)
                actions = device_override[DEVICE_OVERRIDE_ACTIONS]
                if isinstance(actions, list):
                    for item in actions:
                        for key, value in item.items():
                            self.device_override_action(device, key, value, deviceold)
                else:
                    for key, value in actions.items():
                        self.device_override_action(device, key, value, deviceold)
            except BaseException as err:
                _LOGGER.error("Error occurred for device_override. %s - device_override: %s", str(err), str(device_override))
                raise

        if (deviceold is not None):
            fields_edit = []
            for key in device:
                old_value = str(None)
                if (key in deviceold):
                    old_value = str(deviceold[key])
                new_value = str(self.device_override_get_attr_str(device, key))
                if old_value != new_value:
                    fields_edit.append(str(key) + ": '" + str(old_value) + "' -> '" + str(new_value) + "'")
            if len(fields_edit) > 0:
                _LOGGER.debug(
                    "Overriding attributes per object_name: '" + deviceold["object_name"] + "': " + " - ".join(fields_edit) + "."
                )

    def match_name(self, name, search, searchRegex):
        match = False
        if (search is not None):
           match = search == "*" or name.upper() == search.upper()

        #gestione filtro con regex, come su https://gist.github.com/elbarsal/65f413b60d1c4976a8351fba4b4d94d5 (whitelist_re)
        try:
            if (searchRegex is not None):
              name_match = re.search(searchRegex, name, re.IGNORECASE) is not None
              if (name_match):
                #_LOGGER.debug("Whitelist regex matches entity or domain: %s", state.entity_id)
                match = True
        except BaseException as err:
            _LOGGER.error("Error occurred in match_name. name: '" + name + "', searchRegex: '" + searchRegex + "' - %s", str(err))

        return match

    def replace_name(self, name, pattern, repl):
        try:
            if (pattern is not None and repl is not None ):
               name = re.sub(pattern, repl, name, flags=re.I)
        except BaseException as err:
            _LOGGER.error("Error occurred in replace_name. name: '" + name + "', pattern: '" + pattern + "', repl: '" + repl + "' - %s", str(err))
        return name

    def device_override_fix_filter(self, device_override, name, search, searchRegex):
        search = device_override.get(search)
        if (search is not None):
            if (device_override.get(DEVICE_OVERRIDE_FILTER) is None):
                device_override[DEVICE_OVERRIDE_FILTER] = {}
            device_override[DEVICE_OVERRIDE_FILTER][name] = search
        searchRegex = device_override.get(searchRegex)
        if (searchRegex is not None):
            if (device_override.get(DEVICE_OVERRIDE_FILTER_RE) is None):
                device_override[DEVICE_OVERRIDE_FILTER_RE] = {}
            device_override[DEVICE_OVERRIDE_FILTER_RE][name] = searchRegex

    def device_override_fix(self, device_override):
        #if (device_override.get('fixed') is not None):
        #    return
        self.device_override_fix_filter(device_override, 'object_name', "filter_vimar_name", "filter_vimar_name_regex")
        self.device_override_fix_filter(device_override, 'object_name', "filter_object_name", "filter_object_name_regex")
        self.device_override_fix_filter(device_override, 'friendly_name', "filter_friendly_name", "filter_friendly_name_regex")
        self.device_override_fix_filter(device_override, 'object_id', "filter_object_id", "filter_object_id_regex")
        self.device_override_fix_filter(device_override, 'room_name', "filter_room_name", "filter_room_name_regex")
        if (device_override.get(DEVICE_OVERRIDE_ACTIONS) is None):
            device_override[DEVICE_OVERRIDE_ACTIONS] = {}
        actions = device_override[DEVICE_OVERRIDE_ACTIONS]
        if device_override.get("object_name_as_vimar") or device_override.get("friendly_name_as_vimar") :
            actions[DEVICE_OVERRIDE_ACTION_FRIENDLY_NAME_AS_VIMAR] = True
        if device_override.get("friendly_name_room_name_at_begin"):
            actions[DEVICE_OVERRIDE_ACTION_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN] = True
        if device_override.get("friendly_name_regexsub_pattern") is not None:
            actions[DEVICE_OVERRIDE_ACTION_REPLACE_RE] = {
                DEVICE_OVERRIDE_ACTION_REPLACE_RE_FIELD : 'friendly_name',
                DEVICE_OVERRIDE_ACTION_REPLACE_RE_PATTERN : device_override.get("friendly_name_regexsub_pattern") ,
                DEVICE_OVERRIDE_ACTION_REPLACE_RE_REPL : device_override.get("friendly_name_regexsub_repl")
            }

        if device_override.get("friendly_name") is not None:
            actions["friendly_name"] = device_override.get("friendly_name")
        if device_override.get("device_type") is not None:
            actions["device_type"] = device_override.get("device_type")
        if device_override.get("device_class") is not None:
            actions["device_class"] = device_override.get("device_class")
        if device_override.get("icon") is not None:
            actions["icon"] = device_override.get("icon")

        #device_override.fixed = True

    def device_override_get_attr_key(self, key):
        if (key == 'type' or key == 'class' or key == 'friendly_name'):
            return "device_" + key

        if key == 'vimar_object_type':
            return 'object_type'
        if key == 'vimar_object_name':
            return 'object_name'
        if key == 'vimar_object_id':
            return 'object_id'
        if key == 'vimar_room_name':
            return 'room_name'
        if key == 'vimar_room_names':
            return 'room_names'
        return key

    def device_override_get_attr_str(self, device, key):
        attr_name = self.device_override_get_attr_key(key)
        attr_str = device.get(attr_name)
        if attr_str is None:
            attr_str = ""
        elif isinstance(attr_str, list):
            attr_str = ",".join(attr_str)
        return attr_str

    def device_override_match(self, device, device_override):
        #self.device_override_fix(device_override)
        matchcnt = 0
        filters = device_override.get(DEVICE_OVERRIDE_FILTER)
        if isinstance(filters, str) and filters == "*":
            matchcnt += 1
        elif filters is not None:
            for key, value in filters.items():
                attr_str = self.device_override_get_attr_str(device, key)
                if self.match_name(attr_str, value, None) is False:
                    return False
                matchcnt += 1
        filters = device_override.get(DEVICE_OVERRIDE_FILTER_RE)
        if isinstance(filters, str) and filters == "*":
            matchcnt += 1
        elif filters is not None:
            for key, value in filters.items():
                attr_str = self.device_override_get_attr_str(device, key)
                if self.match_name(attr_str, None, value) is False:
                    return False
                matchcnt += 1
        match = matchcnt > 0
        return match


    def device_override_action(self, device, action, value, device_original):
        field = None
        if (action == DEVICE_OVERRIDE_ACTION_FRIENDLY_NAME_AS_VIMAR):
            device["device_friendly_name"] = device["object_name"].title().strip()
            if (device_original is not None):
                device_original["device_friendly_name"] = device["device_friendly_name"]
        elif (action == DEVICE_OVERRIDE_ACTION_FRIENDLY_NAME_ROOM_NAME_AT_BEGIN):
            room_name = ''
            if "room_name" in device and device["room_name"] is not None and device["room_name"] != '':
                room_name = device["room_name"].title().strip()
            if room_name != '':
                friendly_name = device["device_friendly_name"]
                if friendly_name.upper().endswith(room_name.upper()):
                    friendly_name = friendly_name[:-len(room_name)]
                    friendly_name = (room_name + ' ' + friendly_name).strip()
                if not friendly_name.upper().startswith(room_name.upper()):
                    friendly_name = (room_name + ' ' + friendly_name).strip()
                device["device_friendly_name"] = friendly_name
        elif (action == DEVICE_OVERRIDE_ACTION_REPLACE_RE):
            field = self.device_override_get_attr_key(value.get(DEVICE_OVERRIDE_ACTION_REPLACE_RE_FIELD))
            curr_value = self.device_override_get_attr_str(device, field)
            new_value = self.replace_name(curr_value, value.get(DEVICE_OVERRIDE_ACTION_REPLACE_RE_PATTERN), value.get(DEVICE_OVERRIDE_ACTION_REPLACE_RE_REPL))
            device[field] = new_value
        else: #on default, set specified value in dictionary :)
            field = self.device_override_get_attr_key(action)
            device[field] = value

        if (field == 'icon' and isinstance(device[field], str) and "," in device[field]):
            device[field] = device[field].split(",")

