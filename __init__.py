"""
Updated
- Panel layout > updated to match 2.8 styling
- Added cleaner eye toggles for past and future
- Icons to some buttons

Added
- Option to work with linked rigs > needs work InBetween as we need to target Parent rig
- In Front option > show mesh in front of onion skinning
- Shortcuts > for easier and faster workflow
- Addon preferences so shortcuts can be customized
- Panel feedback when nothings is selected or wrong object > updated slight. When onion obj in scene keep showing
- Changing mode now auto-updates > a lot smoother > perhaps do that with all settings? It would mean lots of calculations running
- Auto-update > updates onion object on opening file or when settings Mode, step change > Faster workflow
- InBetweening can be toggle independed now, also can be turned of like other modes

Fixed
- Possibly old onion skinning when another file is openened
- Linked rigs and local object/mesh also show onion skinning
- InBetweening always shows, also when both future and past are disabled
- Old print statement in registers
- anmx_data type was not removed on deactiveing addon

Todo
- Updated on load_post
- No active object with linked setup causes drawing issue

Ideas
- Auto update when working on posing > could be handy? > need feedback from real animators
  > Simply add a bool and add update tool all props then use update_function to redraw
- Added option to do multiple objects > this would need merge of objects, not sure will still work properly

# 2023-08-23
# Fixed
# - issue with starting from linked rig
"""

##################
#Initiation
##################

bl_info = {
    "name": "AnimExtras",
    "author": "Andrew Combs, Rombout Versluijs",
    "version": (1, 1, 7),
    "blender": (2, 80, 0),
    "description": "True onion skinning",
    "category": "Animation",
    "wiki_url": "https://github.com/iBrushC/animextras",
	"tracker_url": "https://github.com/iBrushC/animextras/issues" 
}

import bpy
import rna_keymap_ui
from bpy.types import AddonPreferences

from .ons.gui import *
from .ons import ops
from .ons import registers


class ANMX_AddonPreferences(AddonPreferences):
    """ Preference Settings Addon Panel"""
    bl_idname = __name__
    bl_label = "Addon Preferences"
    bl_options = {'REGISTER', 'UNDO'}

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.label(text = "Hotkeys:")
        col.label(text = "Do NOT remove hotkeys, disable them instead!")

        col.separator()
        wm = bpy.context.window_manager
        kc = wm.keyconfigs.user

        col.separator()
        km = kc.keymaps["3D View"]

        kmi = registers.get_hotkey_entry_item(km, "anim_extras.update_onion","EXECUTE","tab")
        if kmi:
            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
        else:
            col.label(text = "Update Onion Object")
            col.label(text = "restore hotkeys from interface tab")
        col.separator()
        
        kmi = registers.get_hotkey_entry_item(km, "anim_extras.toggle_onion","EXECUTE","tab")
        if kmi:
            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
        else:
            col.label(text = "Toggle Draw Onion")
            col.label(text = "restore hotkeys from interface tab")
        col.separator()
        
        kmi = registers.get_hotkey_entry_item(km, "anim_extras.add_clear_onion","EXECUTE","tab")
        if kmi:
            col.context_pointer_set("keymap", km)
            rna_keymap_ui.draw_kmi([], kc, km, kmi, col, 0)
        else:
            col.label(text = "Add / Clear Onion Object")
            col.label(text = "restore hotkeys from interface tab")
        col.separator()


addon_keymaps = []
classes = [ANMX_gui, ANMX_data, ANMX_set_onion, ANMX_draw_meshes, ANMX_clear_onion, ANMX_toggle_onion, ANMX_update_onion, ANMX_add_clear_onion, ANMX_AddonPreferences]
global _delay
_delay = 10

@persistent
def ANMX_clear_handler(dummy):
    ops.clear_active(clrObj=False, clrRig=False)
    anmx = bpy.context.scene.anmx_data
    if ANMX_draw_meshes.handler is not None:
        ANMX_draw_meshes.unregister_handlers(None, bpy.context)

    if anmx.onion_object != "" and anmx.auto_update and anmx.toggle:
        bpy.ops.anim_extras.update_onion()
        bpy.ops.anim_extras.draw_meshes('INVOKE_DEFAULT')
    # else:
    #     anmx.toggle = False

    #     ANMX_draw_meshes.finish(None,bpy.context)
    # ANMX_draw_meshes.unregister_handlers(ANMX_draw_meshes.handler, bpy.context)
    # bpy.ops.anim_extras.draw_meshes('INVOKE_DEFAULT')

# Very buggy, shortcut is more convenient plus less demanding of the system
"""
def execute_queued_functions():
    anmx = bpy.context.scene.anmx_data
    obj = bpy.context.active_object
    print("#### _delay {} ####".format(_delay))
    if obj.mode == 'POSE' and anmx.auto_key:
        print("#### _delay {} ####".format(float(getattr(anmx,"key_intval"))))
        bpy.ops.anim_extras.update_onion()
        return float(getattr(anmx,"key_intval"))
    return _delay

@persistent
def ANMX_update_pose(dummy):
    obj = bpy.context.active_object
    anmx = bpy.context.scene.anmx_data
    global _delay 
    _delay = 10  
    # _timer = False
    # bpy.app.timers.register(execute_queued_functions)
    # timer = bpy.context.window_manager.event_timer_add(1, window=bpy.context.window)
    if ANMX_draw_meshes.handler is not None and bpy.context.selected_objects != []:
        if anmx.onion_object != "" and anmx.auto_update and anmx.toggle:
            onionObj = anmx.onion_object
            onObj = [obj for obj in bpy.context.selected_objects if ('{0}'.format(onionObj)) in obj.name]
            if onObj !=[]:
                if onObj[0].name == bpy.context.active_object.name:
                    _delay = 1
                    print("#### _delay {} ####".format(_delay))
                    bpy.app.timers.register(execute_queued_functions)
            if obj.mode == 'POSE':
                if _delay == 1:
                    _delay = 10    
                    print("#### _delay {} ####".format(_delay))
  """             

def register():
    for c in classes:
        bpy.utils.register_class(c)
    
    bpy.types.Scene.anmx_data = bpy.props.PointerProperty(type=ANMX_data)
    bpy.app.handlers.load_post.append(ANMX_clear_handler)
    
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    km = kc.keymaps.new(name="3D View", space_type="VIEW_3D")

    kmi = km.keymap_items.new("anim_extras.update_onion", "R", "PRESS", alt = True, shift = True)
    addon_keymaps.append((km, kmi))
    
    kmi = km.keymap_items.new("anim_extras.toggle_onion", "T", "PRESS", alt = True, shift = True)
    addon_keymaps.append((km, kmi))
    
    kmi = km.keymap_items.new("anim_extras.add_clear_onion", "C", "PRESS", alt = True, shift = True)
    addon_keymaps.append((km, kmi))


def unregister():
    bpy.app.handlers.load_post.remove(ANMX_clear_handler)
    
    for c in classes:
        bpy.utils.unregister_class(c)

    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    del bpy.types.Scene.anmx_data

if __name__ == "__main__":
    register()
