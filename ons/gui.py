#######################
## Onion Skinning GUI
#######################

import bpy
from .ops import *


class ANMX_gui(bpy.types.Panel):
    """Panel for all Onion Skinning Operations"""
    bl_idname = 'VIEW3D_PT_animextras_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'AnimExtras'
    bl_label = 'Onion Skinning'

    
    def draw(self, context):
        layout = self.layout
        scn = context.scene
        anmx = context.scene.anmx_data
        obj = context.active_object

        # Makes UI split like 2.8 no split factor 0.3 needed
        layout.use_property_split = True
        layout.use_property_decorate = False
        
        if obj:
            # Show info to user when ietm is not linked or animated
            if not (hasattr(obj.animation_data,"action")) and obj.instance_collection == None:
                layout.label(text="Selected object has no animation", icon='INFO')
            # if context.selected_objects == [] and anmx.onion_object == "":
            #     layout.label(text="Nothing selected", icon='INFO')
        # Makes sure the user can't do any operations when the onion object doesn't exist
        if anmx.onion_object not in bpy.data.objects:
            layout.operator("anim_extras.set_onion")
            return
            # return
        # if not ((obj.type == 'MESH') and hasattr(obj.animation_data,"action") or (obj.type=='EMPTY')):
        #     layout.label(text="Update needs active object", icon='INFO')
            # return    
        else:
            row = layout.row(align=True)
            # sub = row.row(align=True)
            row.prop(anmx, "auto_update", text="", icon="FILE_REFRESH", toggle=True)
            sub = row.row(align=True)
            sub.enabled = anmx.auto_update == False
            sub.operator("anim_extras.update_onion", text="Update")
            # row = row
            row.operator("anim_extras.clear_onion", text="Clear")
            layout.separator(factor=0.2)
        
        
        col = layout.column()
        # col.prop(anmx,"onion_object", text="Current", emboss=False, icon='OUTLINER_OB_MESH') #text="{}".format(anmx.onion_object), 
        # Issue when using emboss=false > the whole column receives this. Feels like a API bug
        if not obj.type == 'ARMATURE':
            col.label(text="Please select RIG", icon='INFO')
            # return
        else:
            col.prop(anmx,"set_onion_object", text="Onion Object", icon='OUTLINER_OB_MESH') #text="{}".format(anmx.onion_object), 
        
        col = layout.column()
        col.prop(anmx, "onion_mode", text="Method")
        
        modes = {"PFS", "INB"}
        # if not anmx.onion_mode in modes: #
        if anmx.onion_mode != "PFS":
            row = layout.row()
            row.prop(anmx, "skin_count", text="Amount")

        if anmx.onion_mode == "PFS":
            col = layout.column(align=True)
            col.prop(anmx, "skin_count", text="Amount")
            col.prop(anmx, "skin_step", text="Step")
        
        text = "Past"
        if anmx.onion_mode == "INB":
            text = "Inbetween Color"
        
        row = layout.row(align=True)
        box = row.box()
        col = box.column(align=True)
        past = col.row(align=True)
        icoPast = 'HIDE_OFF' if anmx.past_enabled else 'HIDE_ON'
        past.row().prop(anmx, "past_enabled", text='', icon=icoPast, emboss=False)
        past.row().label(text=text)
        col.prop(anmx, "past_color", text="")
        col.prop(anmx, "past_opacity_start", text="Start Opacity", slider=True)
        col.prop(anmx, "past_opacity_end", text="End Opacity", slider=True)        
        
        text = "Future"

        if anmx.onion_mode == "INB":
            text = "Direct Keying Color"
        
        box = row.box()
        col = box.column(align=True)
        fut = col.row(align=True)
        icoFut = 'HIDE_OFF' if anmx.future_enabled else 'HIDE_ON'
        fut.prop(anmx, "future_enabled", text='', icon=icoFut, emboss=False)
        fut.label(text=text)
        col.prop(anmx, "future_color", text="")
        col.prop(anmx, "future_opacity_start", text="Start Opacity", slider=True)
        col.prop(anmx, "future_opacity_end", text="End Opacity", slider=True)
        
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.
        layout.separator(factor=0.2)
        if (bpy.app.version[1] < 92):
            col = layout.column(align=True)
            col.label(text="Options")
        else:
            col = layout.column(heading="Options", align=True)
        col.prop(anmx, "use_xray")
        col.prop(anmx, "use_flat")
        col.prop(anmx, "in_front")

        # col.use_property_split = True
        # col.use_property_decorate = False

        # if scn.tool_settings.use_keyframe_insert_auto:
        #     key = col.column(align=True)
        #     # key.enabled = (scn.tool_settings.use_keyframe_insert_auto and (obj.mode == 'POSE')) == True
        #     key.prop(anmx, "auto_key")
        #     # key = layout.column(heading="Interval", align=True)
        #     key.prop(anmx, "key_intval", text="Interval", icon="SORTTIME")
 
        layout.use_property_split = False
        layout.separator(factor=0.2)
        
        text = "Draw"
        if anmx.toggle:
            text = "Stop Drawing"
        icoOni = 'ONIONSKIN_OFF' if anmx.toggle else 'ONIONSKIN_ON'
        layout.prop(anmx, "toggle", text=text, toggle=True, icon=icoOni)