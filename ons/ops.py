#############################
## Onion Skinning Operators
#############################

import bpy
from bpy.app.handlers import persistent
from bpy.types import Operator, PropertyGroup, SpaceView3D
import gpu
import bgl
from gpu_extras.batch import batch_for_shader

import numpy as np
from mathutils import Vector, Matrix

# ########################################################## #
# Data (stroring it in the object or scene doesnt work well) #
# ########################################################## #

shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
frame_data = dict([])
batches = dict([])
extern_data = dict([])

# ################ #
# Functions        #
# ################ #


def update_onion(self, context):
    # anmx = context.scene.anmx_data
    if "anmx_data" in context.scene:
        if context.scene.anmx_data.auto_update:
            bpy.ops.anim_extras.update_onion()

def check_selected(context):
    anmx = context.scene.anmx_data
    obj = context.active_object
    return context.selected_objects != [] or anmx.onion_object != ""
        # return True
        # Need workaround so we can pose and still do updates
        # return ((obj.type == 'MESH') and hasattr(obj.animation_data,"action") or (obj.type=='EMPTY') or (obj.type == 'MESH') and hasattr(obj.parent.animation_data,"action"))
    #     if ((obj.type == 'MESH') and hasattr(obj.animation_data,"action") or (obj.type=='EMPTY')):
    #         return True
    # else:
    #     return False
    
def frame_get_set(_obj, frame):
    scn = bpy.context.scene
    anmx = scn.anmx_data

    # Show from viewport > keep off this allows in_front to work
    # if "_animextras" in scn.collection.children:
    #     vlayer = scn.view_layers['View Layer']
    #     vlayer.layer_collection.children['_animextras'].hide_viewport = False

    if _obj.type == 'EMPTY':
        if anmx.is_linked:
            bpy.ops.object.duplicate_move_linked(OBJECT_OT_duplicate={"linked":True})
            # Hide original but keep it able to render
            _obj.hide_viewport = True
            if "_animextras" in scn.collection.children:
                bpy.data.collections['_animextras'].objects.link(bpy.data.objects[anmx.onion_object])
            # bpy.ops.object.move_to_collection(collection_index=0, is_new=True, new_collection_name="_animextras")

        _obj = bpy.context.active_object
        
        # bpy.ops.object.move_to_collection(collection_index=0, is_new=True, new_collection_name="_animextras")
        if not "_animextras" in scn.collection.children:
            bpy.ops.object.move_to_collection(collection_index=0, is_new=True, new_collection_name="_animextras")
            # bpy.data.collections['_animextras'].hide_viewport = True
            # bpy.data.scenes["Scene"].view_layers[0].layer_collection.collection.children["_animextras"].hide_viewport = False
            bpy.data.collections['_animextras'].hide_render = True
            _obj = bpy.context.selected_objects[0]
        
        # print("_obj %s" % _obj)
        # Linked Rig
        if anmx.is_linked:
            if not "_animextras" in bpy.data.collections['_animextras']:
                bpy.ops.object.make_override_library()
                # Force visibly armature so we can use set_onion_object
                for col in bpy.data.collections:
                    if 'Hidden 11' in col.name:
                        # bpy.data.collections['Hidden 11'].hide_render = False
                        bpy.data.collections[col.name].hide_viewport = False
                        if bpy.data.collections[anmx.onion_object]:
                            for rig in bpy.data.collections[anmx.onion_object].all_objects:
                                # print("rig.type %s" % rig.type)
                                if rig.type == 'ARMATURE':
                                    bpy.context.view_layer.objects.active = bpy.data.objects[rig.name]
                                    anmx.rig_object = rig.name

                for ob in bpy.context.selected_objects:
                    ob.hide_viewport = False
                    if not ob.name in bpy.data.collections['_animextras'].all_objects:
                        bpy.data.collections['_animextras'].objects.link(ob)
                # bpy.ops.object.move_to_collection(collection_index=2)
            # for i in bpy.data.collections['_animextras'].children[0].objects:
            for i in bpy.data.collections['_animextras'].all_objects:
                if i.type == 'MESH':
                    new_onion = i.name
                    i.hide_render = True

            # bpy.context.area.tag_redraw()

            # Make object active so panel shows
            bpy.context.view_layer.objects.active = bpy.data.objects[anmx.rig_object]
        
            scn.anmx_data.onion_object = new_onion
            scn.anmx_data.set_onion_object = new_onion # Test if we can select mesh by using loop count
            anmx.is_linked = False

        # Return duplicated linked rig made local     
        _obj =  bpy.data.objects[anmx.onion_object]
        
        # Dirty workaround, the GUI doesnt seem to be updated at this point
        try:
            # Make object active so panel shows
            bpy.context.view_layer.objects.active = bpy.data.objects[anmx.rig_object]
        except:
            pass

       
	# Gets all of the data from a mesh on a certain frame
    tmpobj = _obj

    # Setting the frame to get an accurate reading of the object on the selected frame
    scn = bpy.context.scene
    scn.frame_set(frame)

    # Getting the Depenency Graph and the evaluated object
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval = tmpobj.evaluated_get(depsgraph)

    # Making a new mesh from the object.
    mesh = eval.to_mesh()
    mesh.update()
    
    # Getting the object's world matrix
    mat = Matrix(_obj.matrix_world)
    
    # This moves the mesh by the object's world matrix, thus making everything global space. This is much faster than getting each vertex individually and doing a matrix multiplication on it
    mesh.transform(mat)
    mesh.update()
    
    # loop triangles are needed to properly draw the mesh on screen
    mesh.calc_loop_triangles()
    mesh.update()
    
    # Creating empties so that all of the verts and indices can be gathered all at once in the next step
    vertices = np.empty((len(mesh.vertices), 3), 'f')
    indices = np.empty((len(mesh.loop_triangles), 3), 'i')
    
    # Getting all of the vertices and incices all at once (from: https://docs.blender.org/api/current/gpu.html#mesh-with-random-vertex-colors)
    mesh.vertices.foreach_get(
        "co", np.reshape(vertices, len(mesh.vertices) * 3))
    mesh.loop_triangles.foreach_get(
        "vertices", np.reshape(indices, len(mesh.loop_triangles) * 3))
    
    args = [vertices, indices]
    
    # Hide from viewport > keep off this allows in_front to work
    # if "_animextras" in scn.collection.children:
    #     vlayer = scn.view_layers['View Layer']
    #     vlayer.layer_collection.children['_animextras'].hide_viewport = True

    return args


def set_to_active(_obj):
    """ Sets the object that is being used for the onion skinning """
    scn = bpy.context.scene
    anmx = scn.anmx_data
    
    # Clear all data > caused double drawing with mode switch
    # Old clear method caused issues when using a rig
    # Still see handler issue
    frame_data.clear()
    batches.clear()
    extern_data.clear()

    # skip clear if we are linked
    if hasattr(anmx,"link_parent"):
        if not anmx.link_parent == "":
            clear_active(clrObj=True, clrRig=False)

    anmx.onion_object = _obj.name
    anmx.is_linked = True if _obj.type == 'EMPTY' else False
    
    if anmx.is_linked:
        if hasattr(anmx,"link_parent"):
            if not anmx.link_parent:
                anmx.link_parent = _obj.name
                # anmx.rig_object = _obj.parent.name

    bake_frames()
    make_batches()


def clear_active(clrObj=False,clrRig=False):
    """ clrRig will do complete clear, used with linked Rigs, allows to update it without deleting everything """
    """ Clears the active object """ 

    scn = bpy.context.scene
    anmx = scn.anmx_data
    name = anmx.onion_object
    
    # Clears all the data needed to store onion skins on the previously selected object
    frame_data.clear()
    batches.clear()
    extern_data.clear()
    
    # Clear localzed rigs & overrides linked items
    if clrRig:
        if hasattr(anmx,"link_parent"):
            if not anmx.link_parent == "":
                bpy.data.collections["_animextras"].objects.unlink(bpy.data.objects[name])
                # fixed clearing error 24082023
                # bpy.data.collections["_animextras"].children[0].objects.unlink(bpy.data.objects[name])
                bpy.data.collections.remove(bpy.data.collections[anmx.link_parent])
                bpy.data.collections.remove(bpy.data.collections["_animextras"])
                # Show original linked rig again
                bpy.data.objects[anmx.link_parent].hide_viewport = False
                anmx.link_parent = ""

    # Gets rid of the selected object
    if clrObj:
        anmx.onion_object = ""
        anmx.rig_object = ""
    # if ANMX_draw_meshes.handler is not None:
    #     ANMX_draw_meshes.finish(None,bpy.context)


def make_batches():
    # Custom OSL shader could be set here
    scn = bpy.context.scene
    anmx = scn.anmx_data
    _obj = bpy.data.objects[anmx.onion_object]
    
    
    for key in frame_data:
        arg = frame_data[key]  # Dictionaries are used rather than lists or arrays so that frame numbers are a given
        vertices = arg[0]
        indices = arg[1]
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)
        batches[key] = batch
        

def bake_frames():
    # Needs to do the following:
    # 1. Bake the data for every frame and store it in the objects "["frame_data"]" items
    scn = bpy.context.scene
    anmx = scn.anmx_data
    _obj = bpy.data.objects[anmx.onion_object]
    
    curr = scn.frame_current
    step = anmx.skin_step
    
    # Getting the first and last frame of the animation
    keyobj = _obj
    
    if _obj.parent is not None:
        keyobj = _obj.parent
    # Check if obj is linked rig
    elif hasattr(_obj.instance_collection, "all_objects"):
        keyobj = _obj.instance_collection.all_objects[_obj.name]
        # print(keyobj)
        # keyobj = _obj.parent

    keyframes = []
    for fc in keyobj.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            keyframes.append(int(k.co[0]))
            
    keyframes = np.unique(keyframes)

    start = int(np.min(keyframes))
    end = int(np.max(keyframes)) + 1
    
    if anmx.onion_mode == "PF":
        for f in range(start, end):
            arg = frame_get_set(_obj, f)
            frame_data[str(f)] = arg
        extern_data.clear()
        
    elif anmx.onion_mode == "PFS":
        for f in range(start, end, step):
            arg = frame_get_set(_obj, f)
            frame_data[str(f)] = arg
        extern_data.clear()
        
    elif anmx.onion_mode == "DC":
        for fkey in keyframes:
            arg = frame_get_set(_obj, fkey)
            frame_data[str(fkey)] = arg
        extern_data.clear()
        
    elif anmx.onion_mode == "INB":
        for f in range(start, end):
            arg = frame_get_set(_obj, f)
            frame_data[str(f)] = arg

        extern_data.clear()
        for fkey in keyframes: 
            extern_data[str(fkey)] = fkey

    scn.frame_set(curr)
    

# ################ #
# Properties       #
# ################ #

class ANMX_data(PropertyGroup):
    # Custom update function for the toggle
    def toggle_update(self, context):
        if self.toggle:
            bpy.ops.anim_extras.draw_meshes('INVOKE_DEFAULT')
        # if ANMX_draw_meshes.handler is not None:
        #     ANMX_draw_meshes.finish(self,bpy.context)
        return

    def inFront(self,context):
        scn = bpy.context.scene
        anmx = scn.anmx_data
        if self.onion_object:
            obj = bpy.context.view_layer.objects.active = bpy.data.objects[self.onion_object]
            obj.show_in_front = True if anmx.in_front else False
            if "use_xray" in anmx:
                if anmx.use_xray:
                    anmx.use_xray = False if anmx.in_front else True
        return

    def update_onionobject_from_rig(self, context):
        anmx = context.scene.anmx_data
        # print(type(anmx.set_onion_object))
        # print(anmx.set_onion_object)
        # print("self %s" % anmx.get_rig_childs(context)[int(anmx.set_onion_object)])
        # print("self %s" % (anmx.get_rig_childs(self["set_onion_object"][1])))
        context.scene.anmx_data.onion_object = anmx.set_onion_object
        if anmx.auto_update:
            bpy.ops.anim_extras.update_onion()

    def get_rig_childs(self, context):
        rig_child_list = []
        rig_child_list.append(("Select", "Select RIG", "", 0))
        try:
            aob = context.active_object
            childs = aob.children
            chld=1
            for i in childs:
                rig_child_list.append((i.name, i.name, "", chld))
                chld+=1
            return rig_child_list
        except AttributeError:
            pass

        return rig_child_list

    modes = [
        ("PF", "Per-Frame", "Shows the amount of frames in the future and past", 1), 
        ("PFS", "Per-Frame Stepped", "Shows the amount of frames in the future and past with option to step-over frames. This allows to see futher but still have a clear overview what is happening", 2), 
        ("DC", "Direct Keys", "Show onion only on inserted keys using amount as frame when keys are visible", 3), 
        ("INB", "Inbetweening", " Inbetweening, lets you see frames with direct keyframes in a different color than interpolated frames", 4)
        ]

    # Auto-update
    auto_update: bpy.props.BoolProperty(name="Auto Update", description="Updates onion object on step change which normally need manual update. Also auto updates opening files with active onion object. Setting is saved per blend file.", default=False)
    auto_key: bpy.props.BoolProperty(name="Use Auto Keying", description="This will run a timer and starting updating automatically, it only work when using auto-keying.", default=False)
    key_intval: bpy.props.EnumProperty(name="AutoKeying Interval", description="Speed of interval of auto updating while use auto keying",default="3", items=[("0.75","0.75 Second","0.75"),("1","1 Second","1"),("1.5","1.5 Second","1.5"),("2","2 Seconds","2"),("2.5","2.5 Seconds","2.5"),("3","3 Second","3"),("3.5","3.5 Seconds","3.5"),("4","4 Seconds","4"),("5","5 Second","5"),("6","6 Second","6"),("7","7 Second","7"),("8","8 Second","8"),("9","9 Second","9"),("10","10 Seconds","10")])
    
    # Onion Skinning Properties
    skin_count: bpy.props.IntProperty(name="Count", description="Number of frames we see in past and future", default=1, min=1) # works without update update=update_onion) We cant update if anmx_data is not made yet?!
    skin_step: bpy.props.IntProperty(name="Step", description="Number of frames to skip in conjuction with Count", default=1, min=1, update=update_onion) #, updaet=update_onion)
    onion_object: bpy.props.StringProperty(name="Onion Object", default="")
    rig_object: bpy.props.StringProperty(name="Rig Object", default="")
    set_onion_object: bpy.props.EnumProperty(name="Set Onion Object", items = get_rig_childs, update=update_onionobject_from_rig)
    onion_mode: bpy.props.EnumProperty(name="", get=None, set=None, items=modes)
    use_xray: bpy.props.BoolProperty(name="Use X-Ray", description="Draws the onion visible through the object", default=False)
    use_flat: bpy.props.BoolProperty(name="Flat Colors", description="Colors while not use opacity showing 100% of the color", default=False)
    in_front: bpy.props.BoolProperty(name="In Front", description="Draws the selected object in front of the onion skinning", default=False, update=inFront)
    toggle: bpy.props.BoolProperty(name="Draw", description="Toggles onion skinning on or off", default=False, update=toggle_update)
    
    # Linked settings
    is_linked: bpy.props.BoolProperty(name="Is linked", default=False)
    link_parent: bpy.props.StringProperty(name="Link Parent", default="")

    # Past settings
    past_color: bpy.props.FloatVectorProperty(name="Past Color", min=0, max=1, size=3, default=(1., .1, .1), subtype='COLOR')
    past_opacity_start: bpy.props.FloatProperty(name="Starting Opacity", min=0, max=1, precision=2, default=0.5)
    past_opacity_end: bpy.props.FloatProperty(name="Ending Opacity", min=0, max=1, precision=2, default=0.1)
    past_enabled: bpy.props.BoolProperty(name="Enabled?", default=True)
    
    # Future settings
    future_color: bpy.props.FloatVectorProperty(name="Future Color", min=0, max=1, size=3, default=(.1, .4, 1.), subtype='COLOR')
    future_opacity_start: bpy.props.FloatProperty(name="Starting Opacity", min=0, max=1,precision=2, default=0.5)
    future_opacity_end: bpy.props.FloatProperty(name="Ending Opacity", min=0, max=1,precision=2, default=0.1)
    future_enabled: bpy.props.BoolProperty(name="Enabled?", default=True)


# ################ #
# Operators        #
# ################ #

class ANMX_set_onion(Operator):
    bl_idname = "anim_extras.set_onion"
    bl_label = "Set Onion To Selected"    
    bl_description = "Sets the selected object to be the onion object"
    bl_options = {'REGISTER', 'UNDO' }
    
    @classmethod
    def poll(cls, context):
        obj = context.active_object
        if context.selected_objects != []:
            if (hasattr(obj.parent,"animation_data") and (obj.type == 'MESH')):
                if (hasattr(obj.parent.animation_data,"action")):
                    return True
            if hasattr(obj.animation_data,"action"):
                if hasattr(obj.animation_data.action,"fcurves"):
                    return ((obj.type == 'MESH') and hasattr(obj.animation_data,"action") or (obj.type=='EMPTY'))
            if hasattr(obj.instance_collection, "all_objects"):
                return True
    
    def execute(self, context):
        obj = context.active_object
        scn = context.scene
        anmx = scn.anmx_data

        #Extra check for the shortcuts
        if not check_selected(context):
            self.report({'INFO'}, "Onion needs animated active selection ")
            return {'CANCELLED'}  

        if anmx.toggle == False:
            anmx.toggle = False if anmx.toggle else True

        if obj == None:
            return {"CANCELLED"}
        
        if obj.parent is None:
            try:
                obj.animation_data.action.fcurves
            except AttributeError:
                pass
                # return {"CANCELLED"}
        else:
            try:
                # This right here needs to change for allowing linked rigs
                # obj.parent.animation_data.action.fcurves
                dObj = bpy.data.objects[obj.name]
                hasattr(dObj.instance_collection, "all_objects")
            except AttributeError:
                return {"CANCELLED"}
        
        # Or check if it is linked empty
        if ((obj.type == 'MESH') or (obj.type=='EMPTY')):
            set_to_active(obj)
    
        return {"FINISHED"}


class ANMX_clear_onion(Operator):
    bl_idname = "anim_extras.clear_onion"
    bl_label = "Clear Selected Onion"
    bl_description = "Clears onion object, does store the settings in scene untile other ojbect is set as active onion object."
    bl_options = {'REGISTER', 'UNDO' }
   
    def execute(self, context):
        #Extra check for the shortcuts
        if not check_selected(context):
            self.report({'INFO'}, "Onion needs animated active selection")
            return {'CANCELLED'}

        clear_active(clrObj=True, clrRig=True)

        return {"FINISHED"}
    
class ANMX_toggle_onion(Operator):
    """ Operator for toggling the onion object so we can shortcut it"""
    bl_idname = "anim_extras.toggle_onion"
    bl_label = "Toggle Onion"
    bl_description = "Toggles onion ON/OFF"
    bl_options = {'REGISTER', 'UNDO' }
    
    def execute(self, context):
        anmx = context.scene.anmx_data
        anmx.toggle = False if anmx.toggle else True
    
        return {"FINISHED"}

class ANMX_add_clear_onion(Operator):
    """ Toggle for clearing and adding"""
    bl_idname = "anim_extras.add_clear_onion"
    bl_label = "Add/Toggle Onion"
    bl_description = "Add/Toggles onion ON/OFF"
    bl_options = {'REGISTER', 'UNDO' }
    
    def execute(self, context):
        #Extra check for the shortcuts
        if not check_selected(context):
            self.report({'INFO'}, "Onion needs animated active selection")
            return {'CANCELLED'}

        anmx = context.scene.anmx_data
        if anmx.onion_object=="":
            bpy.ops.anim_extras.set_onion()
        else:
            bpy.ops.anim_extras.clear_onion()

        return {"FINISHED"}


class ANMX_update_onion(Operator):
    bl_idname = "anim_extras.update_onion"
    bl_label = "Update Selected Onion"
    bl_description = "Updates the path of the onion object"
    bl_options = {'REGISTER', 'UNDO' }
    
    def execute(self, context):
        anmx = context.scene.anmx_data
        #Extra check for the shortcuts
        if not check_selected(context):
            self.report({'INFO'}, "Onion needs active selection")
            return {'CANCELLED'}

        # This allows to update, also pose mode
        if anmx.onion_object in bpy.data.objects:
            set_to_active(bpy.data.objects[anmx.onion_object])
    
        return {"FINISHED"}

# Uses a list formatted in the following way to draw the meshes:
# [[vertices, indices, colors], [vertices, indices, colors]]
class ANMX_draw_meshes(Operator):
    bl_idname = "anim_extras.draw_meshes"
    bl_label = "Draw Onion Skinning"
    bl_description = "Draws a set of meshes without creating objects"
    bl_options = {'REGISTER', 'UNDO' }
    
    handler = None

    def __init__(self):
        # self.handler = None
        self.mode = None
        # self.amount = None
        # self.steps = None
    
    # def __del__(self):
    #     cls = ANMX_draw_meshes
    # #     """ unregister when done, helps when reopening other scenes """
    # #     # self.finish(bpy.context)
    #     if cls.handler == None:
    #         self.unregister_handlers(self, bpy.context)
            # self.unregister_handlers(self, bpy.context)

    def invoke(self, context, event):
        self.register_handlers(self,context)
        context.window_manager.modal_handler_add(self)
        anmx = context.scene.anmx_data
        self.mode = anmx.onion_mode
        # Causes a crash?
        # self.amount = anmx.skin_count
        # self.steps = anmx.skin_steps
        return {'RUNNING_MODAL'}

    @staticmethod
    def register_handlers(self, context):
        cls = ANMX_draw_meshes
        if cls.handler == None:
            cls.handler = SpaceView3D.draw_handler_add(self.draw_callback, (context,), 'WINDOW', 'POST_VIEW')
            # context.area.tag_redraw()
    
    @staticmethod
    def unregister_handlers(self, context):
        cls = ANMX_draw_meshes
        if cls.handler != None:
            # context.area.tag_redraw()
            SpaceView3D.draw_handler_remove(cls.handler, 'WINDOW')
        cls.handler = None
        context.scene.anmx_data.toggle = False

    def modal(self, context, event):
        anmx = context.scene.anmx_data
        scn = context.scene
        autok = scn.tool_settings.use_keyframe_insert_auto
        
        # Auto Keying-pose mode 
        if self.mode != anmx.onion_mode and anmx.auto_update and autok: #(anmx.anmx_auto_key and autok):
            self.mode = anmx.onion_mode
            bpy.ops.anim_extras.update_onion()
            pass
        # Auto update 
        if self.mode != anmx.onion_mode and anmx.auto_update:
            self.mode = anmx.onion_mode
            bpy.ops.anim_extras.update_onion()
            pass
        # Also auto update for modes only
        if self.mode != anmx.onion_mode:
            self.mode = anmx.onion_mode
            bpy.ops.anim_extras.update_onion()
            pass
        # if self.amount != anmx.skin_count:
        #     print("#### ANMX > Count update ####")
        #     self.amount = anmx.skin_count
        #     bpy.ops.anim_extras.update_onion()
        #     pass
        # if self.steps != anmx.skin_steps:
        #     print("#### ANMX > Steps update ####")
        #     self.steps = anmx.skin_steps
        #     bpy.ops.anim_extras.update_onion()
        #     pass
        if anmx.onion_object not in bpy.data.objects:
            # self.unregister_handlers()
            self.unregister_handlers(self,context)
            return {'CANCELLED'}

        if anmx.toggle is False or self.mode != anmx.onion_mode:
            self.unregister_handlers(self,context)
            return {'CANCELLED'}
        
        return {'PASS_THROUGH'}

    # def execute(self, context):
    #     if context.area.type == 'VIEW_3D':
    #         if context.window_manager.measureit_run_opengl is False:
    #             self.handle_add(self, context)
    #             # context.area.tag_redraw()
    #         else:
    #             self.handle_remove(self, context)
    #             # context.area.tag_redraw()

    #         return {'FINISHED'}
    #     else:
    #         self.report({'WARNING'},
    #                     "View3D not found, cannot run operator")

    #     return {'CANCELLED'}
    
    def finish(self, context):
        self.unregister_handlers(self,context)
        # SpaceView3D.draw_handler_remove(cls.handler, bpy.context)
        # SpaceView3D.draw_handler_remove(None, bpy.context)
        return {'FINISHED'}
    
    def draw_callback(self, context):
        scn = context.scene
        ac = scn.anmx_data
        f = scn.frame_current

        pc = ac.past_color
        fc = ac.future_color

        override = False
        color = (0, 0, 0, 0)
        threshold = ac.skin_count
        
        if context.space_data.overlay.show_overlays == False:
            return
        
        for key in batches:
            f_dif = abs(f-int(key))

            # Getting the color if the batch is in the past
            if len(extern_data) == 0:
                if f > int(key):
                    if ac.past_enabled:
                        color = (pc[0], pc[1], pc[2], ac.past_opacity_start-((ac.past_opacity_start-ac.past_opacity_end)/ac.skin_count) * f_dif)
                    else:
                        override = True
                # Getting the color if the batch is in the future
                else:
                    if ac.future_enabled:
                        color = (fc[0], fc[1], fc[2], ac.future_opacity_start-((ac.future_opacity_start-ac.future_opacity_end)/ac.skin_count) * f_dif)
                    else:
                        override = True
            else:
                # if ac.future_enabled or ac.past_enabled:
                if key in extern_data:
                    if ac.future_enabled:
                        color = (fc[0], fc[1], fc[2], ac.future_opacity_start-((ac.future_opacity_start-ac.future_opacity_end)/ac.skin_count) * f_dif)
                    else:
                        override = True
                else:
                    if ac.past_enabled:
                        color = (pc[0], pc[1], pc[2], ac.past_opacity_start-((ac.past_opacity_start-ac.past_opacity_end)/ac.skin_count) * f_dif)
                    else:
                        override = True
            # Only draws if the frame is not the current one, it is within the skin limits, and there has not been an override
            if f != int(key) and f_dif <= ac.skin_count and not override:
                shader.bind()
                shader.uniform_float("color", color)
                
                # Theres gotta be a better way to do this. Seems super inefficient
                if not ac.use_flat:
                    bgl.glEnable(bgl.GL_BLEND)
                    bgl.glEnable(bgl.GL_CULL_FACE)
                if not ac.use_xray:
                    bgl.glEnable(bgl.GL_DEPTH_TEST)
                
                batches[key].draw(shader)
                
                bgl.glDisable(bgl.GL_BLEND)
                bgl.glDisable(bgl.GL_CULL_FACE)
                bgl.glDisable(bgl.GL_DEPTH_TEST)
            
            override = False