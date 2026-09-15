#!/usr/bin/python
"""
    K40 Whisperer

    Copyright (C) <2017-2026>  <Scorch>
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
version = '0.71'
title_text = "K40 Whisperer V"+version

import sys
from math import *
from egv import egv
from nano_library import K40_CLASS
from svg_reader import SVG_READER
from svg_reader import SVG_TEXT_EXCEPTION
from svg_reader import SVG_PXPI_EXCEPTION
from g_code_library import G_Code_Rip
from interpolate import interpolate
from ecoords import ECoord
from convex_hull import hull2D
from embedded_images import K40_Whisperer_Images
from modern_importers import import_dxf
from k40core.configuration import (ConfigurationError, configuration_path,
                                   load_configuration, save_configuration)
from k40core.coordinates import display_y, origin_for_reference
from k40core.arrays import array_steps, instance_array_bounds, maximum_array_counts
from k40core.legacy import vector_lines_in_inches
from k40core.model import Bounds, InstanceArray, Operation, Point
from k40core.transforms import (apply_document_transform, editable_bounds,
                                reflection, rotation, uniform_scale)
from k40core.preview import (iter_preview_polylines, model_origin_canvas,
                             rectangular_trace, ruler_values,
                             transparent_raster_preview)
from k40core.rasterizer import dpi_for_pixel_budget, rasterize_fills
from k40core.raster_paths import extract_scanlines
from k40core.safety import WorkAreaError, placed_job_bounds, validate_work_area

import inkex
import simplestyle
import simpletransform
import cubicsuperpath
import cspsubdiv
import traceback
import struct

DEBUG = False

if DEBUG:
    import inspect
    
VERSION = sys.version_info[0]
LOAD_MSG = ""

if VERSION == 3:
    from tkinter import *
    from tkinter.filedialog import *
    import tkinter.messagebox
    from tkinter import ttk
    MAXINT = sys.maxsize
    def trace_variable(variable, callback):
        return variable.trace_add("write", callback)
    def trace_delete(variable,callback):
        return variable.trace_remove("write",callback)
    
else:
    from Tkinter import *
    from tkFileDialog import *
    import tkMessageBox
    import ttk
    MAXINT = sys.maxint
    def trace_variable(variable, callback):
        return variable.trace_variable("w", callback)
    def trace_delete(variable,callback):
        return variable.trace_vdelete("w",callback)

if VERSION < 3 and sys.version_info[1] < 6:
    def next(item):
        #return item.next()
        return item.__next__()

import math
from time import time
import os
import re
import binascii
import getopt
import operator
import webbrowser
import queue
import threading
from PIL import Image
from PIL import ImageOps
from PIL import ImageFilter
from PIL import ImageDraw

try:
    Image.warnings.simplefilter('ignore', Image.DecompressionBombWarning)
except:
    pass
try:
    from PIL import ImageTk
    from PIL import _imaging
except:
    pass #Don't worry everything will still work

try:
    Image.LANCZOS
except:
    Image.LANCZOS=Image.ANTIALIAS

PYCLIPPER=True
try:
    import pyclipper
except:
    print("Unable to load Pyclipper library (Offset trace outline will not work without it)")
    PYCLIPPER = False

try:
    os.chdir(os.path.dirname(__file__))
except:
    pass

QUIET = False
   
################################################################################
class Application(Frame):
    def __init__(self, master):
        self.trace_window = toplevel_dummy()
        self.dxf_import_thread = None
        self.dxf_import_queue = None
        self.dxf_import_cancel = None
        self.dxf_progress_indeterminate = False
        self.preview_render_generation = 0
        self.preview_line_buffer = None
        self.preview_render_active = False
        self.job_document = None
        self.array_build_thread = None
        self.array_build_queue = None
        self.array_previous_arrays = None
        Frame.__init__(self, master)
        self.w = 780
        self.h = 490
        frame = Frame(master, width= self.w, height=self.h)
        self.master = master
        self.x = -1
        self.y = -1
        self.createWidgets()
        self.master.protocol("WM_DELETE_WINDOW", lambda: self.Quit_Click(None))
        self.micro = False
        

    def resetPath(self):
        self.RengData  = ECoord()
        self.VengData  = ECoord()
        self.VcutData  = ECoord()
        self.GcodeData = ECoord()
        self.SCALE = 1
        self.Design_bounds = (0,0,0,0)
        self.UI_image = None
        self.job_document = None
        self.source_raster_dpi = 0.0
        #if self.HomeUR.get():
        self.move_head_window_temporary([0.0,0.0])
        #else:
        #    self.move_head_window_temporary([0.0,0.0])
            
        self.pos_offset=[0.0,0.0]

    def make_ui_icon(self, name, size=20, color="#0b2b5c"):
        """Cria ícones consistentes em memória usando apenas Pillow."""
        scale = size / 24.0
        def p(value):
            return int(round(value * scale))

        # Ícones usados junto de texto recebem uma pequena margem transparente
        # à direita. Isso separa visualmente o símbolo do rótulo sem caracteres
        # ou espaços artificiais no texto do botão.
        icon_width = size if name.startswith("arrow_") else size + 6
        image = Image.new("RGBA", (icon_width, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        width = max(2, p(2))

        if name == "plug":
            # Silhueta sólida e limpa, no estilo do plug clássico da Font Awesome.
            draw.rounded_rectangle((p(6), p(1), p(9), p(9)), radius=p(1), fill=color)
            draw.rounded_rectangle((p(15), p(1), p(18), p(9)), radius=p(1), fill=color)
            draw.rounded_rectangle((p(4), p(7), p(20), p(15)), radius=p(3), fill=color)
            draw.polygon(((p(6),p(13)),(p(18),p(13)),(p(17),p(17)),
                          (p(14),p(20)),(p(14),p(23)),(p(10),p(23)),
                          (p(10),p(20)),(p(7),p(17))), fill=color)
        elif name == "folder":
            draw.polygon(((p(2),p(7)),(p(9),p(7)),(p(11),p(9)),(p(22),p(9)),(p(20),p(20)),(p(3),p(20))), fill=color)
            draw.rounded_rectangle((p(2),p(5),p(10),p(10)), radius=p(1), fill=color)
        elif name == "reload":
            draw.arc((p(3),p(3),p(21),p(21)), 35, 320, fill=color, width=width)
            draw.polygon(((p(18),p(2)),(p(23),p(3)),(p(20),p(8))), fill=color)
        elif name == "copies":
            draw.rounded_rectangle((p(3),p(3),p(15),p(15)), radius=p(1),
                                   outline=color, width=width)
            draw.rounded_rectangle((p(9),p(9),p(21),p(21)), radius=p(1),
                                   fill="white", outline=color, width=width)
        elif name == "transform":
            draw.rectangle((p(4),p(4),p(16),p(16)), outline=color, width=width)
            draw.line((p(12),p(1),p(12),p(8)), fill=color, width=width)
            draw.polygon(((p(12),p(1)),(p(8),p(6)),(p(16),p(6))), fill=color)
            draw.line((p(19),p(12),p(12),p(12)), fill=color, width=width)
            draw.polygon(((p(19),p(12)),(p(14),p(8)),(p(14),p(16))), fill=color)
        elif name in ("mirror_horizontal", "mirror_vertical"):
            # Duas formas refletidas e um eixo pontilhado, padrão visual de espelhamento.
            if name == "mirror_horizontal":
                draw.polygon(((p(2),p(5)),(p(9),p(9)),(p(9),p(15)),(p(2),p(19))),
                             outline=color, width=width)
                draw.polygon(((p(22),p(5)),(p(15),p(9)),(p(15),p(15)),(p(22),p(19))),
                             outline=color, width=width)
                for y in range(p(2), p(23), max(2, p(5))):
                    draw.line((p(12),y,p(12),min(y+p(2),p(23))), fill=color, width=width)
            else:
                draw.polygon(((p(5),p(2)),(p(9),p(9)),(p(15),p(9)),(p(19),p(2))),
                             outline=color, width=width)
                draw.polygon(((p(5),p(22)),(p(9),p(15)),(p(15),p(15)),(p(19),p(22))),
                             outline=color, width=width)
                for x in range(p(2), p(23), max(2, p(5))):
                    draw.line((x,p(12),min(x+p(2),p(23)),p(12)), fill=color, width=width)
        elif name == "preview":
            draw.rectangle((p(3),p(5),p(21),p(19)), outline=color, width=width)
            draw.polygon(((p(10),p(8)),(p(17),p(12)),(p(10),p(16))), fill=color)
        elif name == "home":
            draw.polygon(((p(2),p(11)),(p(12),p(2)),(p(22),p(11))), fill=color)
            draw.rectangle((p(5),p(10),p(19),p(21)), fill=color)
            draw.rectangle((p(10),p(14),p(14),p(21)), fill="white")
        elif name == "unlock":
            draw.arc((p(6),p(1),p(17),p(14)), 170, 350, fill=color, width=width)
            draw.rounded_rectangle((p(5),p(10),p(20),p(22)), radius=p(2), fill=color)
            draw.ellipse((p(11),p(14),p(14),p(17)), fill="white")
        elif name == "target":
            draw.ellipse((p(5),p(5),p(19),p(19)), outline=color, width=width)
            draw.ellipse((p(10),p(10),p(14),p(14)), fill=color)
            draw.line((p(12),p(1),p(12),p(7)), fill=color, width=width)
            draw.line((p(12),p(17),p(12),p(23)), fill=color, width=width)
            draw.line((p(1),p(12),p(7),p(12)), fill=color, width=width)
            draw.line((p(17),p(12),p(23),p(12)), fill=color, width=width)
        elif name == "play":
            draw.polygon(((p(7),p(4)),(p(20),p(12)),(p(7),p(20))), fill=color)
        elif name == "pause":
            draw.rounded_rectangle((p(5),p(4),p(10),p(20)), radius=p(1), fill=color)
            draw.rounded_rectangle((p(14),p(4),p(19),p(20)), radius=p(1), fill=color)
        elif name == "stop":
            draw.rounded_rectangle((p(5),p(5),p(19),p(19)), radius=p(2), fill=color)
        elif name.startswith("arrow_"):
            points = {
                "arrow_up": ((p(12),p(3)),(p(21),p(13)),(p(16),p(13)),(p(16),p(21)),(p(8),p(21)),(p(8),p(13)),(p(3),p(13))),
                "arrow_down": ((p(8),p(3)),(p(16),p(3)),(p(16),p(11)),(p(21),p(11)),(p(12),p(21)),(p(3),p(11)),(p(8),p(11))),
                "arrow_left": ((p(3),p(12)),(p(13),p(3)),(p(13),p(8)),(p(21),p(8)),(p(21),p(16)),(p(13),p(16)),(p(13),p(21))),
                "arrow_right": ((p(21),p(12)),(p(11),p(3)),(p(11),p(8)),(p(3),p(8)),(p(3),p(16)),(p(11),p(16)),(p(11),p(21))),
            }
            draw.polygon(points[name], fill=color)

        return ImageTk.PhotoImage(image)
        
    def createWidgets(self):
        self.initComplete = 0
        self.stop=[True]
        self.job_paused = False
        self.job_running = False
        self.connection_state = "no_board"
        
        self.k40        = None
        self.run_time   = 0
        self.display_power = False
        self.display_test  = False
        self.pi_mode_height = 625
        
        self.master.bind("<Configure>", self.Master_Configure)
        self.master.bind('<Enter>', self.bindConfigure)
        self.master.bind('<F1>', self.KEY_F1)
        self.master.bind('<F2>', self.KEY_F2)
        self.master.bind('<F3>', self.KEY_F3)
        self.master.bind('<F4>', self.KEY_F4)
        self.master.bind('<F5>', self.KEY_F5)
        self.master.bind('<F6>', self.KEY_F6)
        self.master.bind('<Home>', self.Home)

        #self.master.bind('<Control-R>', self.Raster_Eng)
        #self.master.bind('<Control-V>', self.Vector_Eng)
        #self.master.bind('<Control-C>', self.Vector_Cut)
        #self.master.bind('<Control-G>', self.Gcode_Cut)

        self.master.bind('<Control-Left>'  , self.Move_Left)
        self.master.bind('<Control-Right>' , self.Move_Right)
        self.master.bind('<Control-Up>'    , self.Move_Up)
        self.master.bind('<Control-Down>'  , self.Move_Down)
        
        self.master.bind('<Control-Home>'  , self.Move_UL)
        self.master.bind('<Control-Prior>' , self.Move_UR)
        self.master.bind('<Control-Next>'  , self.Move_LR)
        self.master.bind('<Control-End>'   , self.Move_LL)
        self.master.bind('<Control-Clear>' , self.Move_CC)

        self.master.bind('<Control-Key-4>' , self.Move_Left)
        self.master.bind('<Control-6>'     , self.Move_Right)
        self.master.bind('<Control-8>'     , self.Move_Up)
        self.master.bind('<Control-Key-2>' , self.Move_Down)
        
        self.master.bind('<Control-7>'     , self.Move_UL)
        self.master.bind('<Control-9>'     , self.Move_UR)
        self.master.bind('<Control-Key-3>' , self.Move_LR)
        self.master.bind('<Control-Key-1>' , self.Move_LL)
        self.master.bind('<Control-Key-5>' , self.Move_CC)

        #####

        self.master.bind('<Alt-Control-Left>' , self.Move_Arb_Left)
        self.master.bind('<Alt-Control-Right>', self.Move_Arb_Right)
        self.master.bind('<Alt-Control-Up>'   , self.Move_Arb_Up)
        self.master.bind('<Alt-Control-Down>' , self.Move_Arb_Down)

        self.master.bind('<Alt-Control-Key-4>', self.Move_Arb_Left)
        self.master.bind('<Alt-Control-6>'    , self.Move_Arb_Right)
        self.master.bind('<Alt-Control-8>'    , self.Move_Arb_Up)
        self.master.bind('<Alt-Control-Key-2>', self.Move_Arb_Down)


        self.master.bind('<Alt-Left>' , self.Move_Arb_Left)
        self.master.bind('<Alt-Right>', self.Move_Arb_Right)
        self.master.bind('<Alt-Up>'   , self.Move_Arb_Up)
        self.master.bind('<Alt-Down>' , self.Move_Arb_Down)

        self.master.bind('<Alt-Key-4>', self.Move_Arb_Left)
        self.master.bind('<Alt-6>'    , self.Move_Arb_Right)
        self.master.bind('<Alt-8>'    , self.Move_Arb_Up)
        self.master.bind('<Alt-Key-2>', self.Move_Arb_Down)

        #####
        self.master.bind('<Control-i>' , self.Initialize_Laser)
        self.master.bind('<Control-f>' , self.Unfreeze_Laser)
        self.master.bind('<Control-o>' , self.menu_File_Open_Design)
        self.master.bind('<Control-l>' , self.menu_Reload_Design)
        self.master.bind('<Control-h>' , self.Home)
        self.master.bind('<Control-u>' , self.Unlock)
        self.master.bind('<Escape>'    , self.Stop_Job)
        self.master.bind('<Control-t>' , self.TRACE_Settings_Window)

        self.include_Reng = BooleanVar()
        self.include_Rpth = BooleanVar()
        self.include_Veng = BooleanVar()
        self.include_Vcut = BooleanVar()
        self.include_Gcde = BooleanVar()
        self.include_Time = BooleanVar()

        # Seleção das operações que serão executadas pelo gerenciador do trabalho.
        # Estas variáveis são independentes das opções do menu Visualizar.
        self.run_Reng = BooleanVar()
        self.run_Veng = BooleanVar()
        self.run_Vcut = BooleanVar()
        self.run_Gcde = BooleanVar()

        self.advanced     = BooleanVar()
        self.show_power   = BooleanVar()
        self.show_test    = BooleanVar()
        
        self.halftone     = BooleanVar()
        self.mirror       = BooleanVar()
        self.rotate       = BooleanVar()
        self.negate       = BooleanVar()
        self.inputCSYS    = BooleanVar()
        self.HomeUR       = BooleanVar()
        self.engraveUP    = BooleanVar()
        self.init_home    = BooleanVar()
        self.post_home    = BooleanVar()
        self.post_beep    = BooleanVar()
        self.post_disp    = BooleanVar()
        self.post_exec    = BooleanVar()
        
        self.pre_pr_crc   = BooleanVar()
        self.inside_first = BooleanVar()
        self.rotary       = BooleanVar()
        self.reduced_mem  = BooleanVar()
        self.wait         = BooleanVar()
        

        self.ht_size    = StringVar()
        self.Reng_feed  = StringVar()
        self.Veng_feed  = StringVar()
        self.Vcut_feed  = StringVar()

        self.Reng_power  = StringVar()
        self.Veng_power  = StringVar()
        self.Vcut_power  = StringVar()
        self.Gcode_power = StringVar()
        self.Trace_power = StringVar()
        self.max_power   = StringVar()
        self.test_power  = StringVar()
        self.test_time   = StringVar()

        self.Reng_passes = StringVar()
        self.Veng_passes = StringVar()
        self.Vcut_passes = StringVar()
        self.Gcde_passes = StringVar()
        
        
        self.board_name = StringVar()
        self.units      = StringVar()
        self.jog_step   = StringVar()
        self.rast_step  = StringVar()
        self.funits     = StringVar()
        self.funits_label=StringVar()
        

        self.bezier_M1     = StringVar()
        self.bezier_M2     = StringVar()
        self.bezier_weight = StringVar()

##        self.unsharp_flag = BooleanVar()
##        self.unsharp_r    = StringVar()
##        self.unsharp_p    = StringVar()
##        self.unsharp_t    = StringVar()
##        self.unsharp_flag.set(False)
##        self.unsharp_r.set("40")
##        self.unsharp_p.set("350")
##        self.unsharp_t.set("3")

        self.LaserXsize = StringVar()
        self.LaserYsize = StringVar()

        self.LaserXscale = StringVar()
        self.LaserYscale = StringVar()
        self.LaserRscale = StringVar()

        self.rapid_feed = StringVar()

        self.gotoX = StringVar()
        self.gotoY = StringVar()

        self.n_egv_passes = StringVar()

        self.inkscape_path = StringVar()
        self.batch_path    = StringVar()
        self.ink_timeout   = StringVar()
        
        self.t_timeout  = StringVar()
        self.n_timeouts  = StringVar()
        
        self.Reng_time = StringVar()
        self.Veng_time = StringVar()
        self.Vcut_time = StringVar()
        self.Gcde_time = StringVar()

        self.comb_engrave = BooleanVar()
        self.comb_vector  = BooleanVar()
        self.zoom2image   = BooleanVar()

        self.trace_w_laser  = BooleanVar()
        self.trace_gap      = StringVar()
        self.trace_speed    = StringVar()
        self.preview_mode   = StringVar()
        
        ###########################################################################
        #                         INITILIZE VARIABLES                             #
        #    if you want to change a default setting this is the place to do it   #
        ###########################################################################
        self.include_Reng.set(1)
        self.include_Rpth.set(0)
        self.include_Veng.set(1)
        self.include_Vcut.set(1)
        self.include_Gcde.set(1)
        self.include_Time.set(1)
        self.advanced.set(0)
        self.run_Reng.set(1)
        self.run_Veng.set(1)
        self.run_Vcut.set(1)
        self.run_Gcde.set(1)
        self.show_power.set(1)
        self.show_test.set(1)
        
        self.halftone.set(1)
        self.mirror.set(0)
        self.rotate.set(0)
        self.negate.set(0)
        self.inputCSYS.set(0)
        self.HomeUR.set(0)
        self.engraveUP.set(0)
        self.init_home.set(1)
        self.post_home.set(0)
        self.post_beep.set(0)
        self.post_disp.set(0)
        self.post_exec.set(0)
        
        self.pre_pr_crc.set(1)
        self.inside_first.set(1)
        self.rotary.set(0)
        self.reduced_mem.set(0)
        self.wait.set(1)
        
        self.ht_size.set(500)

        self.Reng_feed.set("100")
        self.Veng_feed.set("20")
        self.Vcut_feed.set("10")

        self.Reng_power.set("0.5")
        self.Veng_power.set("0.5")
        self.Vcut_power.set("0.5")
        self.Gcode_power.set("0.5")
        self.Trace_power.set("0.5")
        self.max_power.set("30")
        self.test_power.set("0.5")
        self.test_time.set("250")
        
        self.Reng_passes.set("1")
        self.Veng_passes.set("1")
        self.Vcut_passes.set("1")
        self.Gcde_passes.set("1")
        
        
        self.jog_step.set("10.0")
        self.rast_step.set("0.002")
        
        self.bezier_weight.set("3.5")
        self.bezier_M1.set("2.5")
        self.bezier_M2.set("0.50")

        self.bezier_weight_default = float(self.bezier_weight.get())
        self.bezier_M1_default     = float(self.bezier_M1.get())
        self.bezier_M2_default     = float(self.bezier_M2.get())
        
                                        
        self.board_name.set("LASER-M2") # Options are
                                        #    "LASER-M3",
                                        #    "LASER-M2",
                                        #    "LASER-M1",
                                        #    "LASER-M",
                                        #    "LASER-B2",
                                        #    "LASER-B1",
                                        #    "LASER-B",
                                        #    "LASER-A"


        self.units.set("mm")            # Options are "in" and "mm"

        self.ink_timeout.set("3")
        self.t_timeout.set("200")
        self.n_timeouts.set("30")

        self.HOME_DIR    = os.path.expanduser("~")
        
        if not os.path.isdir(self.HOME_DIR):
            self.HOME_DIR = ""

        self.DESIGN_FILE = (self.HOME_DIR+"/None")
        self.EGV_FILE    = None
        
        self.aspect_ratio =  0
        self.segID   = []
        
        self.LaserXsize.set("325")
        self.LaserYsize.set("220")
        
        self.LaserXscale.set("1.000")
        self.LaserYscale.set("1.000")
        self.LaserRscale.set("1.000")

        self.rapid_feed.set("0.0")

        self.gotoX.set("0.000")
        self.gotoY.set("0.000")

        # Valores exibidos no painel de posicionamento. Eles refletem a posição
        # que o K40 Whisperer já mantém internamente e não consultam a placa.
        self.currentX = StringVar()
        self.currentY = StringVar()
        self.currentX.set("0.000")
        self.currentY.set("0.000")

        self.n_egv_passes.set("1")

        self.comb_engrave.set(0)
        self.comb_vector.set(0)
        self.zoom2image.set(0)


        self.trace_w_laser.set(0)
        self.trace_gap.set(0)
        self.trace_speed.set(50)
        self.preview_mode.set("rectangle")
        
        self.laserX    = 0.0
        self.laserY    = 0.0
        self.PlotScale = 1.0
        self.GUI_Disabled = False

        # PAN and ZOOM STUFF
        self.panx = 0
        self.panx = 0
        self.lastx = 0
        self.lasty = 0
        self.move_start_x = 0
        self.move_start_y = 0

        
        self.RengData  = ECoord()
        self.VengData  = ECoord()
        self.VcutData  = ECoord()
        self.GcodeData = ECoord()
        self.SCALE = 1
        self.Design_bounds = (0,0,0,0)
        self.UI_image = None
        self.pos_offset=[0.0,0.0]
        self.inkscape_warning = False
        
        # Derived variables
        if self.units.get() == 'in':
            self.funits.set('in/min')
            self.funits_label.set('Velocidade\npol/min')
            self.units_scale = 1.0
        else:
            self.units.set('mm')
            self.funits.set('mm/s')
            self.funits_label.set('Velocidade\nmm/s')
            self.units_scale = 25.4
        
        self.statusMessage = StringVar()
        self.statusMessage.set("Bem-vindo ao K40 Whisperer")
        
        
        self.Reng_time.set("0")
        self.Veng_time.set("0")
        self.Vcut_time.set("0")
        self.Gcde_time.set("0")

        self.min_vector_speed = 1.1 #in/min
        self.min_raster_speed = 12  #in/min
        
        ##########################################################################
        ###                     END INITILIZING VARIABLES                      ###
        ##########################################################################

        # make a Status Bar
        self.statusbar = Label(self.master, textvariable=self.statusMessage, \
                                   bd=1, relief=SUNKEN , height=1)
        self.statusbar.pack(anchor=SW, fill=X, side=BOTTOM)
        self.import_progress = ttk.Progressbar(
            self.master,
            orient=HORIZONTAL,
            mode="indeterminate",
            maximum=100,
        )
        

        # Canvas
        lbframe = Frame( self.master )
        self.PreviewCanvas_frame = lbframe
        self.PreviewCanvas = Canvas(lbframe, width=self.w-(350+20), height=self.h-200, background="grey75")
        self.PreviewCanvas.pack(side=LEFT, fill=BOTH, expand=1)
        self.PreviewCanvas_frame.place(x=360, y=10)

        self.PreviewCanvas.tag_bind('LaserTag',"<1>"              , self.mousePanStart)
        self.PreviewCanvas.tag_bind('LaserTag',"<B1-Motion>"      , self.mousePan)
        self.PreviewCanvas.tag_bind('LaserTag',"<ButtonRelease-1>", self.mousePanStop)

        self.PreviewCanvas.tag_bind('LaserDot',"<3>"              , self.right_mousePanStart)
        self.PreviewCanvas.tag_bind('LaserDot',"<B3-Motion>"      , self.right_mousePan)
        self.PreviewCanvas.tag_bind('LaserDot',"<ButtonRelease-3>", self.right_mousePanStop)

        # Left Column #
        separator_color = "#c7cdd4"
        self.separator1 = Frame(self.master, height=1, bd=0, relief=FLAT, bg=separator_color)
        self.separator2 = Frame(self.master, height=1, bd=0, relief=FLAT, bg=separator_color)
        self.separator3 = Frame(self.master, height=1, bd=0, relief=FLAT, bg=separator_color)
        self.separator4 = Frame(self.master, height=1, bd=0, relief=FLAT, bg=separator_color)
        self.separator5 = Frame(self.master, height=1, bd=0, relief=FLAT, bg=separator_color)

        #Speed
        self.Label_Reng_feed_u = Label(self.master,textvariable=self.funits, anchor=W)
        self.Entry_Reng_feed   = Entry(self.master,width="15")
        self.Entry_Reng_feed.configure(textvariable=self.Reng_feed,justify='left',fg="black")
        trace_variable(self.Reng_feed, self.Entry_Reng_feed_Callback)
        self.NormalColor =  self.Entry_Reng_feed.cget('bg')

        self.Label_Veng_feed_u = Label(self.master,textvariable=self.funits, anchor=W)
        self.Entry_Veng_feed   = Entry(self.master,width="15")
        self.Entry_Veng_feed.configure(textvariable=self.Veng_feed,justify='left',fg="blue")
        trace_variable(self.Veng_feed, self.Entry_Veng_feed_Callback)
        self.NormalColor =  self.Entry_Veng_feed.cget('bg')

        self.Label_Vcut_feed_u = Label(self.master,textvariable=self.funits, anchor=W)
        self.Entry_Vcut_feed   = Entry(self.master,width="15")
        self.Entry_Vcut_feed.configure(textvariable=self.Vcut_feed,justify='left',fg="red")
        trace_variable(self.Vcut_feed, self.Entry_Vcut_feed_Callback)
        self.NormalColor =  self.Entry_Vcut_feed.cget('bg')

        #Power
        self.Label_feed_u  = Label(self.master,textvariable=self.funits_label, anchor=CENTER)
        self.Label_power_u = Label(text="Fração de\npotência", anchor=CENTER)

        self.Label_time_u  = Label(text="Tempo\nms", anchor=CENTER)
        self.Label_power2_u= Label(text="Fração de\npotência", anchor=CENTER)
                        
        
        self.Entry_Reng_power   = Entry(self.master,width="15")
        self.Entry_Reng_power.configure(textvariable=self.Reng_power,justify='center',fg="black")
        trace_variable(self.Reng_power, self.Entry_Reng_power_Callback)
        self.NormalColor =  self.Entry_Reng_power.cget('bg')

        self.Entry_Veng_power   = Entry(self.master,width="15")
        self.Entry_Veng_power.configure(textvariable=self.Veng_power,justify='center',fg="blue")
        trace_variable(self.Veng_power, self.Entry_Veng_power_Callback)
        self.NormalColor =  self.Entry_Veng_power.cget('bg')

        self.Entry_Vcut_power   = Entry(self.master,width="15")
        self.Entry_Vcut_power.configure(textvariable=self.Vcut_power,justify='center',fg="red")
        trace_variable(self.Vcut_power, self.Entry_Vcut_power_Callback)
        self.NormalColor =  self.Entry_Vcut_power.cget('bg')

        self.Entry_Gcode_power   = Entry(self.master,width="15")
        self.Entry_Gcode_power.configure(textvariable=self.Gcode_power,justify='center',fg="red")
        trace_variable(self.Gcode_power, self.Entry_Gcode_power_Callback)
        self.NormalColor =  self.Entry_Gcode_power.cget('bg')


        ### Test Fire ###
        self.Test_Button  = Button(self.master,text="Testar disparo", command=self.Test_Fire)
        self.Label_Test_time_u = Label(self.master,text="ms", anchor=W)
        self.Entry_Test_time   = Entry(self.master,width="15")
        self.Entry_Test_time.configure(textvariable=self.test_time,justify='center',fg="black")

        trace_variable(self.test_time, self.Entry_Test_time_Callback)
        self.NormalColor =  self.Entry_Test_time.cget('bg')
        
        self.Entry_Test_power   = Entry(self.master,width="15")
        self.Label_Test_power_u = Label(self.master,text="%", anchor=W)
        self.Entry_Test_power.configure(textvariable=self.test_power,justify='center',fg="black")
        trace_variable(self.test_power, self.Entry_Test_power_Callback)
        self.NormalColor =  self.Entry_Test_power.cget('bg')

        ##################
                        
        # Tabela de operações
        self.Reng_Button  = Label(self.master,text="Rasterizar", anchor=W)
        self.Veng_Button  = Label(self.master,text="Gravar", anchor=W)
        self.Vcut_Button  = Label(self.master,text="Cortar", anchor=W)
        self.Grun_Button  = Label(self.master,text="G-code", anchor=W)

        self.Header_Process = Label(self.master,text="Processo", anchor=W)
        self.Header_Enabled = Label(self.master,text="Ativo", anchor=CENTER)
        self.Header_Speed = Label(self.master,text="Velocidade", anchor=CENTER)
        self.Header_Power = Label(self.master,text="Potência", anchor=CENTER)
        self.Header_Passes = Label(self.master,text="Passadas", anchor=CENTER)
        self.Header_Color = Label(self.master,text="Cor", anchor=CENTER)
        self.Table_Lines = [Frame(self.master, bg="#c7cdd4", height=1) for _ in range(5)]

        self.Check_Reng = Checkbutton(self.master,text="", variable=self.run_Reng, anchor=CENTER)
        self.Check_Veng = Checkbutton(self.master,text="", variable=self.run_Veng, anchor=CENTER)
        self.Check_Vcut = Checkbutton(self.master,text="", variable=self.run_Vcut, anchor=CENTER)
        self.Check_Gcde = Checkbutton(self.master,text="", variable=self.run_Gcde, anchor=CENTER)

        self.Color_Reng = Label(self.master,text="", bg="black", relief=SUNKEN, bd=1)
        self.Color_Veng = Label(self.master,text="", bg="blue", relief=SUNKEN, bd=1)
        self.Color_Vcut = Label(self.master,text="", bg="red", relief=SUNKEN, bd=1)
        self.Color_Gcde = Label(self.master,text="", bg="black", relief=SUNKEN, bd=1)
        self.Gcode_Speed_Display = Label(self.master,text="do arquivo", anchor=CENTER, fg="grey35")

        # Sufixos desenhados sobre a área interna dos campos mantêm as variáveis
        # numéricas puras, preservando validação, cálculos e arquivos existentes.
        self.Speed_Units = [Label(self.master, textvariable=self.funits, anchor=E,
                                  bg="white", fg="#59636e", font=("TkDefaultFont", 7))
                            for _ in range(3)]
        self.Passes_Units = [Label(self.master, text="x", anchor=CENTER,
                                   bg="white", fg="#59636e")
                             for _ in range(3)]


        self.Reng_Veng_Button      = Button(self.master,text="Gravar raster\ne vetor", command=self.Raster_Vector_Eng)
        self.Veng_Vcut_Button      = Button(self.master,text="Gravar e\ncortar vetor", command=self.Vector_Eng_Cut)
        self.Reng_Veng_Vcut_Button = Button(self.master,text="Gravar raster\nGravar vetor\ne\nCortar vetor", command=self.Raster_Vector_Cut)
        
        self.Label_Position_Control = Label(self.master,text="Controles de posição:", anchor=W)
        
        self.Initialize_Button = Button(self.master,text="Conectar Laser", command=self.Initialize_Laser)
        # Mantido apenas para compatibilidade interna com layouts antigos.
        self.Connection_Status = Label(self.master,text="", anchor=W)

        self.Open_Button       = Button(self.master,text="Abrir Vetor", command=self.menu_File_Open_Design)
        self.Reload_Button     = Button(self.master,text="Recarregar Vetor", command=self.menu_Reload_Design)
        self.Array_Button      = Button(self.master, text="Múltiplas Cópias",
                                        command=self.MULTIPLE_COPIES_Window)
        self.Edit_Button       = Button(self.master, text="Editar desenho",
                                        command=self.EDIT_VECTOR_Window)
        
        self.Home_Button       = Button(self.master,text="Origem",          command=self.Home)
        self.UnLock_Button     = Button(self.master,text="Liberar eixos",   command=self.Unlock)
        self.Run_Button        = Button(self.master,text="Rodar", bg="#5cb85c", activebackground="#449d44", command=self.Run_Selected)
        self.Pause_Button      = Button(self.master,text="Pausar", bg="#f0ad4e", activebackground="#ec971f", command=self.Pause_Job)
        self.Stop_Button       = Button(self.master,text="Parar", bg="#d9534f", activebackground="#c9302c", command=self.Stop_Job)
        self.Preview_Button    = Button(self.master, text="Preview", bg="#337ab7",
                                        activebackground="#286090",
                                        command=self.Run_Boundary_Preview)
        self.Preview_Menu_Button = Button(self.master, text="▼", bg="#337ab7",
                                           activebackground="#286090",
                                           command=self.Show_Preview_Mode_Menu)

        try:            
            self.left_image  = PhotoImage(data=K40_Whisperer_Images.left_B64,  format='gif')
            self.right_image = PhotoImage(data=K40_Whisperer_Images.right_B64, format='gif')
            self.up_image    = PhotoImage(data=K40_Whisperer_Images.up_B64,    format='gif')
            self.down_image  = PhotoImage(data=K40_Whisperer_Images.down_B64,  format='gif')
            
            self.Right_Button   = Button(self.master,image=self.right_image, command=self.Move_Right)
            self.Left_Button    = Button(self.master,image=self.left_image,  command=self.Move_Left)
            self.Up_Button      = Button(self.master,image=self.up_image,    command=self.Move_Up)
            self.Down_Button    = Button(self.master,image=self.down_image,  command=self.Move_Down)

            self.UL_image  = PhotoImage(data=K40_Whisperer_Images.UL_B64, format='gif')
            self.UR_image  = PhotoImage(data=K40_Whisperer_Images.UR_B64, format='gif')
            self.LR_image  = PhotoImage(data=K40_Whisperer_Images.LR_B64, format='gif')
            self.LL_image  = PhotoImage(data=K40_Whisperer_Images.LL_B64, format='gif')
            self.CC_image  = PhotoImage(data=K40_Whisperer_Images.CC_B64, format='gif')

            self.UL_Button = Button(self.master,image=self.UL_image, command=self.Move_UL)
            self.UR_Button = Button(self.master,image=self.UR_image, command=self.Move_UR)
            self.LR_Button = Button(self.master,image=self.LR_image, command=self.Move_LR)
            self.LL_Button = Button(self.master,image=self.LL_image, command=self.Move_LL)
            self.CC_Button = Button(self.master,image=self.CC_image, command=self.Move_CC)
            
        except:
            self.Right_Button   = Button(self.master,text=">",          command=self.Move_Right)
            self.Left_Button    = Button(self.master,text="<",          command=self.Move_Left)
            self.Up_Button      = Button(self.master,text="^",          command=self.Move_Up)
            self.Down_Button    = Button(self.master,text="v",          command=self.Move_Down)

            self.UL_Button = Button(self.master,text=" ", command=self.Move_UL)
            self.UR_Button = Button(self.master,text=" ", command=self.Move_UR)
            self.LR_Button = Button(self.master,text=" ", command=self.Move_LR)
            self.LL_Button = Button(self.master,text=" ", command=self.Move_LL)
            self.CC_Button = Button(self.master,text=" ", command=self.Move_CC)

        self.Label_Step   = Label(self.master,text="Passo", anchor=W)
        self.Label_Step_u = Label(self.master,textvariable=self.units, anchor=W)
        self.Entry_Step   = Entry(self.master,width="15")
        self.Entry_Step.configure(textvariable=self.jog_step, justify='center')
        trace_variable(self.jog_step, self.Entry_Step_Callback)

        ###########################################################################
        self.GoTo_Button    = Button(self.master,text="Mover para", command=self.GoTo)
        self.Label_Current_Position = Label(self.master,text="Posição atual:", anchor=W)
        self.Display_CurrentX = Label(self.master, anchor=CENTER, textvariable=self.currentX)
        self.Display_CurrentY = Label(self.master, anchor=CENTER, textvariable=self.currentY)

        # Biblioteca visual única. As referências precisam permanecer no objeto
        # para que o Tkinter não descarte as imagens durante a execução.
        self.ui_icons = {
            "plug_gray": self.make_ui_icon("plug", 20, "#6b7280"),
            "plug_yellow": self.make_ui_icon("plug", 20, "#e6a700"),
            "plug_red": self.make_ui_icon("plug", 20, "#dc2626"),
            "plug_green": self.make_ui_icon("plug", 20, "#16a34a"),
            "folder": self.make_ui_icon("folder", 20),
            "reload": self.make_ui_icon("reload", 20),
            "copies": self.make_ui_icon("copies", 20),
            "transform": self.make_ui_icon("transform", 20),
            "mirror_horizontal": self.make_ui_icon("mirror_horizontal", 20),
            "mirror_vertical": self.make_ui_icon("mirror_vertical", 20),
            "preview": self.make_ui_icon("preview", 18, "white"),
            "home": self.make_ui_icon("home", 20),
            "unlock": self.make_ui_icon("unlock", 20),
            "target": self.make_ui_icon("target", 20),
            "target_compact": self.make_ui_icon("target", 16),
            "up": self.make_ui_icon("arrow_up", 22),
            "down": self.make_ui_icon("arrow_down", 22),
            "left": self.make_ui_icon("arrow_left", 22),
            "right": self.make_ui_icon("arrow_right", 22),
            "play": self.make_ui_icon("play", 18, "white"),
            "pause": self.make_ui_icon("pause", 18, "#3b2a00"),
            "stop": self.make_ui_icon("stop", 18, "white"),
        }
        self.Initialize_Button.configure(text="Conectar Laser", image=self.ui_icons["plug_gray"], compound=LEFT)
        self.Initialize_Button.configure(bd=1, relief=RAISED, highlightthickness=0)
        self.Open_Button.configure(image=self.ui_icons["folder"], compound=LEFT)
        self.Reload_Button.configure(image=self.ui_icons["reload"], compound=LEFT)
        self.Array_Button.configure(image=self.ui_icons["copies"], compound=LEFT)
        self.Edit_Button.configure(image=self.ui_icons["transform"], compound=LEFT)
        self.Home_Button.configure(image=self.ui_icons["home"], compound=LEFT)
        self.UnLock_Button.configure(image=self.ui_icons["unlock"], compound=LEFT)
        self.GoTo_Button.configure(image=self.ui_icons["target_compact"], compound=LEFT)
        self.Up_Button.configure(image=self.ui_icons["up"])
        self.Down_Button.configure(image=self.ui_icons["down"])
        self.Left_Button.configure(image=self.ui_icons["left"])
        self.Right_Button.configure(image=self.ui_icons["right"])
        self.Run_Button.configure(image=self.ui_icons["play"], compound=LEFT, fg="white")
        self.Pause_Button.configure(image=self.ui_icons["pause"], compound=LEFT)
        self.Stop_Button.configure(image=self.ui_icons["stop"], compound=LEFT, fg="white")
        self.Preview_Button.configure(image=self.ui_icons["preview"], compound=LEFT,
                                      fg="white", padx=2)
        self.Preview_Menu_Button.configure(fg="white", padx=0)
        for button in (self.Initialize_Button, self.Open_Button, self.Reload_Button,
                       self.Array_Button, self.Edit_Button,
                       self.Home_Button, self.UnLock_Button, self.GoTo_Button,
                       self.Run_Button, self.Pause_Button, self.Stop_Button,
                       self.Preview_Button):
            button.configure(padx=7, pady=2)
        self.GoTo_Button.configure(padx=2)
        
        self.Entry_GoToX   = Entry(self.master,width="15",justify='center')
        self.Entry_GoToX.configure(textvariable=self.gotoX)
        trace_variable(self.gotoX, self.Entry_GoToX_Callback)
        self.Entry_GoToY   = Entry(self.master,width="15",justify='center')
        self.Entry_GoToY.configure(textvariable=self.gotoY)
        trace_variable(self.gotoY, self.Entry_GoToY_Callback)
        self.Entry_GoToX.bind("<FocusOut>", self.Format_Position_Entries)
        self.Entry_GoToY.bind("<FocusOut>", self.Format_Position_Entries)
        self.master.after(300, self.Refresh_Connection_Detection)
        
        self.Label_GoToX   = Label(self.master,text="X", anchor=CENTER )
        self.Label_GoToY   = Label(self.master,text="Y", anchor=CENTER )
        ###########################################################################
        # End Left Column #

        # Advanced Column     #
        self.separator_vert = Frame(self.master, height=2, bd=1, relief=SUNKEN)
        self.Label_Advanced_column = Label(self.master,text="Configurações avançadas",anchor=CENTER)
        self.separator_adv = Frame(self.master, height=2, bd=1, relief=SUNKEN)       

        self.Label_Halftone_adv = Label(self.master,text="Meio-tom (dithering)")
        self.Checkbutton_Halftone_adv = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_Halftone_adv.configure(variable=self.halftone)
        trace_variable(self.halftone, self.View_Refresh_and_Reset_RasterPath) #self.menu_View_Refresh_Callback

        self.Label_Negate_adv = Label(self.master,text="Inverter cores do raster")
        self.Checkbutton_Negate_adv = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_Negate_adv.configure(variable=self.negate)
        trace_variable(self.negate, self.View_Refresh_and_Reset_RasterPath)

        self.separator_adv2 = Frame(self.master, height=2, bd=1, relief=SUNKEN)  

        self.Label_Mirror_adv = Label(self.master,text="Espelhar desenho")
        self.Checkbutton_Mirror_adv = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_Mirror_adv.configure(variable=self.mirror)
        trace_variable(self.mirror, self.View_Refresh_and_Reset_RasterPath)

        self.Label_Rotate_adv = Label(self.master,text="Girar desenho")
        self.Checkbutton_Rotate_adv = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_Rotate_adv.configure(variable=self.rotate)
        trace_variable(self.rotate, self.View_Refresh_and_Reset_RasterPath)

        self.separator_adv3 = Frame(self.master, height=2, bd=1, relief=SUNKEN)
        
        self.Label_inputCSYS_adv = Label(self.master,text="Usar coordenadas da entrada")
        self.Checkbutton_inputCSYS_adv = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_inputCSYS_adv.configure(variable=self.inputCSYS)
        trace_variable(self.inputCSYS, self.menu_View_inputCSYS_Refresh_Callback)

        self.Label_Inside_First_adv = Label(self.master,text="Cortar interior primeiro")
        self.Checkbutton_Inside_First_adv = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_Inside_First_adv.configure(variable=self.inside_first)
        trace_variable(self.inside_first, self.menu_Inside_First_Callback)

        self.Label_Inside_First_adv = Label(self.master,text="Cortar interior primeiro")
        self.Checkbutton_Inside_First_adv = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_Inside_First_adv.configure(variable=self.inside_first)

        self.Label_Rotary_Enable_adv = Label(self.master,text="Usar configurações do rotativo")
        self.Checkbutton_Rotary_Enable_adv = Checkbutton(self.master,text="")
        self.Checkbutton_Rotary_Enable_adv.configure(variable=self.rotary)
        trace_variable(self.rotary, self.Reset_RasterPath_and_Update_Time)


        #####
        self.separator_comb = Frame(self.master, height=2, bd=1, relief=SUNKEN)  

        self.Label_Comb_Engrave_adv = Label(self.master,text="Agrupar tarefas de gravação")
        self.Checkbutton_Comb_Engrave_adv = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_Comb_Engrave_adv.configure(variable=self.comb_engrave)
        trace_variable(self.comb_engrave, self.menu_View_Refresh_Callback)

        self.Label_Comb_Vector_adv = Label(self.master,text="Agrupar tarefas vetoriais")
        self.Checkbutton_Comb_Vector_adv = Checkbutton(self.master,text=" ", anchor=W)
        self.Checkbutton_Comb_Vector_adv.configure(variable=self.comb_vector)
        trace_variable(self.comb_vector, self.menu_View_Refresh_Callback) 
        #####
        
        self.Label_Reng_passes = Label(self.master,text="Pass.:", anchor=E)
        self.Entry_Reng_passes   = Entry(self.master,width="15")
        self.Entry_Reng_passes.configure(textvariable=self.Reng_passes,justify='left',fg="black")
        trace_variable(self.Reng_passes, self.Entry_Reng_passes_Callback)
        self.NormalColor =  self.Entry_Reng_passes.cget('bg')

        self.Label_Veng_passes = Label(self.master,text="Pass.:", anchor=E)
        self.Entry_Veng_passes   = Entry(self.master,width="15")
        self.Entry_Veng_passes.configure(textvariable=self.Veng_passes,justify='left',fg="blue")
        trace_variable(self.Veng_passes, self.Entry_Veng_passes_Callback)
        self.NormalColor =  self.Entry_Veng_passes.cget('bg')

        self.Label_Vcut_passes = Label(self.master,text="Pass.:", anchor=E)
        self.Entry_Vcut_passes   = Entry(self.master,width="15")
        self.Entry_Vcut_passes.configure(textvariable=self.Vcut_passes,justify='left',fg="red")
        trace_variable(self.Vcut_passes, self.Entry_Vcut_passes_Callback)
        self.NormalColor =  self.Entry_Vcut_passes.cget('bg')

        self.Label_Gcde_passes = Label(self.master,text="Pass.:", anchor=E)
        self.Entry_Gcde_passes   = Entry(self.master,width="15")
        self.Entry_Gcde_passes.configure(textvariable=self.Gcde_passes,justify='center',fg="black")
        trace_variable(self.Gcde_passes, self.Entry_Gcde_passes_Callback)
        self.NormalColor =  self.Entry_Gcde_passes.cget('bg')

        
        self.Hide_Adv_Button = Button(self.master,text="Ocultar avançadas", command=self.Hide_Advanced)
                
        # End Right Column #
        self.calc_button = Button(self.master,text="Calcular tempo do raster", command=self.menu_Calc_Raster_Time)

        #GEN Setting Window Entry initializations
        self.Entry_Sspeed    = Entry()
        self.Entry_BoxGap    = Entry()
        self.Entry_ContAngle = Entry()

        # Make Menu Bar
        self.menuBar = Menu(self.master, relief = "raised", bd=2)

        


        top_File = Menu(self.menuBar, tearoff=0)
        top_File.add("command", label = "Salvar configurações agora", command = self.Save_Auto_Configuration)
        top_File.add("command", label = "Importar configurações legadas", command = self.menu_File_Open_Settings_File)

        top_File.add_separator()
        top_File.add("command", label = "Abrir desenho (SVG/DXF/G-code)", command = self.menu_File_Open_Design)
        top_File.add("command", label = "Recarregar desenho", command = self.menu_Reload_Design)

        top_File.add_separator()    
        top_File.add("command", label = "Enviar arquivo EGV para a laser", command = self.menu_File_Open_EGV)

        SaveEGVmenu = Menu(self.master, relief = "raised", bd=2, tearoff=0)
        top_File.add_cascade(label="Salvar arquivo EGV", menu=SaveEGVmenu)        
        SaveEGVmenu.add("command", label = "Gravação raster", command = self.menu_File_Raster_Engrave)
        SaveEGVmenu.add("command", label = "Gravação vetorial", command = self.menu_File_Vector_Engrave)
        SaveEGVmenu.add("command", label = "Corte vetorial", command = self.menu_File_Vector_Cut)
        SaveEGVmenu.add("command", label = "Operações G-code", command = self.menu_File_G_Code)
        SaveEGVmenu.add_separator()   
        SaveEGVmenu.add("command", label = "Gravação raster e vetorial", command = self.menu_File_Raster_Vector_Engrave)
        SaveEGVmenu.add("command", label = "Gravação e corte vetorial", command = self.menu_File_Vector_Engrave_Cut)
        SaveEGVmenu.add("command", label = "Gravação raster, vetorial e corte vetorial", command = self.menu_File_Raster_Vector_Cut)
        
    
        top_File.add_separator()
        top_File.add("command", label = "Sair", command = self.menu_File_Quit)
        
        self.menuBar.add("cascade", label="Arquivo", menu=top_File)

        #top_Edit = Menu(self.menuBar, tearoff=0)
        #self.menuBar.add("cascade", label="Edit", menu=top_Edit)

        top_View = Menu(self.menuBar, tearoff=0)
        top_View.add("command", label = "Atualizar   <F5>", command = self.menu_View_Refresh)
        top_View.add_separator()
        top_View.add_checkbutton(label = "Mostrar imagem raster", variable=self.include_Reng ,command= self.menu_View_Refresh)
        if DEBUG:
            top_View.add_checkbutton(label = "Mostrar trajetórias raster", variable=self.include_Rpth ,command= self.menu_View_Refresh)
        
        top_View.add_checkbutton(label = "Mostrar gravação vetorial", variable=self.include_Veng ,command= self.menu_View_Refresh)
        top_View.add_checkbutton(label = "Mostrar corte vetorial", variable=self.include_Vcut ,command= self.menu_View_Refresh)
        top_View.add_checkbutton(label = "Mostrar trajetórias G-code", variable=self.include_Gcde ,command= self.menu_View_Refresh)
        top_View.add_separator()
        top_View.add_checkbutton(label = "Ajustar zoom ao desenho", variable=self.zoom2image ,command= self.menu_View_Refresh)

        #top_View.add_separator()
        #top_View.add("command", label = "computeAccurateReng",command= self.computeAccurateReng)
        #top_View.add("command", label = "computeAccurateVeng",command= self.computeAccurateVeng)
        #top_View.add("command", label = "computeAccurateVcut",command= self.computeAccurateVcut)

        self.menuBar.add("cascade", label="Visualizar", menu=top_View)

        top_Tools = Menu(self.menuBar, tearoff=0)
        self.menuBar.add("cascade", label="Ferramentas", menu=top_Tools)
        USBmenu = Menu(self.master, relief = "raised", bd=2, tearoff=0)
          
        top_Tools.add("command", label = "Calcular tempo do raster", command = self.menu_Calc_Raster_Time)
        top_Tools.add("command", label = "Contornar limite do desenho <Ctrl-t>", command = self.TRACE_Settings_Window)
        top_Tools.add_separator()
        top_Tools.add("command", label = "Conectar laser <Ctrl-i>", command = self.Initialize_Laser)
        top_Tools.add("command", label = "Destravar laser <Ctrl-f>", command = self.Unfreeze_Laser)
        top_Tools.add_cascade(label="USB", menu=USBmenu)
        USBmenu.add("command", label = "Redefinir USB", command = self.Reset)
        USBmenu.add("command", label = "Liberar USB", command = self.Release_USB)

                    

        #top_USB = Menu(self.menuBar, tearoff=0)
        #top_USB.add("command", label = "Reset USB", command = self.Reset)
        #top_USB.add("command", label = "Release USB", command = self.Release_USB)
        #top_USB.add("command", label = "Initialize Laser", command = self.Initialize_Laser)
        #self.menuBar.add("cascade", label="USB", menu=top_USB)
        

        top_Settings = Menu(self.menuBar, tearoff=0)
        top_Settings.add("command", label = "Geral e máquina <F2>", command = self.GEN_Settings_Window)
        top_Settings.add("command", label = "Raster <F3>", command = self.RASTER_Settings_Window)
        top_Settings.add("command", label = "Rotativo <F4>", command = self.ROTARY_Settings_Window)
        top_Settings.add_separator()
        top_Settings.add("command", label = "Trabalho e desenho <F6>", command = self.JOB_Settings_Window)
        top_Settings.add_separator()
        top_Settings.add("command", label = "Resetar configurações", command = self.Reset_Configuration)
        
        self.menuBar.add("cascade", label="Configurações", menu=top_Settings)
        
        top_Help = Menu(self.menuBar, tearoff=0)
        top_Help.add("command", label = "Sobre (e-mail)", command = self.menu_Help_About)
        top_Help.add("command", label = "Site do K40 Whisperer", command = self.menu_Help_Web)
        top_Help.add("command", label = "Manual (site)", command = self.menu_Help_Manual)
        self.menuBar.add("cascade", label="Ajuda", menu=top_Help)

        self.master.config(menu=self.menuBar)

        ##########################################################################
        #                  Config File and command line options                  #
        ##########################################################################
        self.config_path = configuration_path(
            __file__, frozen=bool(getattr(sys, "frozen", False))
        )
        self._config_save_after = None
        self._config_ready = False
        self._factory_configuration = self._configuration_values()
        if os.path.isfile(self.config_path):
            self._load_auto_configuration()
        else:
            config_file = "k40_whisperer.txt"
            home_config1 = self.HOME_DIR + "/" + config_file
            if os.path.isfile(config_file):
                self.Open_Settings_File(config_file)
            elif os.path.isfile(home_config1):
                self.Open_Settings_File(home_config1)
            self.include_Time.set(1)
            self._save_configuration()
        self._enable_configuration_autosave()


#        opts, args = None, None
#        try:
#            opts, args = getopt.getopt(sys.argv[1:], "ho:",["help", "other_option"])
#        except:
#            debug_message('Unable interpret command line options')
#            sys.exit()
#        for option, value in opts:
##            if option in ('-h','--help'):
##                fmessage(' ')
##                fmessage('Usage: python .py [-g file]')
##                fmessage('-o    : unknown other option (also --other_option)')
##                fmessage('-h    : print this help (also --help)\n')
##                sys.exit()
#            if option in ('-m','--micro'):
#                self.micro = True

        ##########################################################################

################################################################################
    def entry_set(self, val2, calc_flag=0, new=0):
        if calc_flag == 0 and new==0:
            try:
                self.statusbar.configure( bg = 'yellow' )
                val2.configure( bg = 'yellow' )
                self.statusMessage.set(" É necessário recalcular.")
            except:
                pass
        elif calc_flag == 3:
            try:
                val2.configure( bg = 'red3' )
                self.statusbar.configure( bg = 'red' )
                self.statusMessage.set(" O valor deve ser numérico. ")
            except:
                pass
        elif calc_flag == 2:
            try:
                val2.configure( bg = 'red3' )
                self.statusbar.configure( bg = 'red' )
            except:
                pass
        elif (calc_flag == 0 or calc_flag == 1) and new==1 :
            try:
                self.statusbar.configure( bg = 'white' )
                self.statusMessage.set(" ")
                val2.configure( bg = 'white' )
            except:
                pass
        elif (calc_flag == 1) and new==0 :
            try:
                self.statusbar.configure( bg = 'white' )
                self.statusMessage.set(" ")
                val2.configure( bg = 'white' )
            except:
                pass

        elif (calc_flag == 0 or calc_flag == 1) and new==2:
            return 0
        return 1

################################################################################
    def _configuration_variables(self):
        names = (
            "include_Reng", "include_Rpth", "include_Veng", "include_Vcut",
            "include_Gcde", "advanced", "show_power", "show_test",
            "halftone", "mirror", "rotate", "negate", "inputCSYS", "HomeUR",
            "engraveUP", "init_home", "post_home", "post_beep", "post_disp",
            "post_exec", "pre_pr_crc", "inside_first", "comb_engrave",
            "comb_vector", "zoom2image", "rotary", "reduced_mem", "wait",
            "trace_w_laser", "run_Reng", "run_Veng", "run_Vcut", "run_Gcde",
            "Reng_feed", "Veng_feed", "Vcut_feed", "Reng_power", "Veng_power",
            "Vcut_power", "Gcode_power", "Trace_power", "max_power",
            "Reng_passes", "Veng_passes", "Vcut_passes", "Gcde_passes",
            "rast_step", "ht_size", "jog_step", "board_name", "units",
            "LaserXsize", "LaserYsize", "LaserXscale", "LaserYscale",
            "LaserRscale", "rapid_feed", "bezier_M1", "bezier_M2",
            "bezier_weight", "trace_gap", "trace_speed", "test_time",
            "test_power", "t_timeout", "n_timeouts", "ink_timeout",
            "inkscape_path", "batch_path", "preview_mode",
        )
        return {name: getattr(self, name) for name in names}

    def _configuration_values(self):
        return {name: variable.get()
                for name, variable in self._configuration_variables().items()}

    def _apply_configuration(self, settings):
        variables = self._configuration_variables()
        for name, value in settings.items():
            variable = variables.get(name)
            if variable is not None:
                if name == "gotoY":
                    # Configuration files predating the positive-Y interface
                    # may still contain the old internal negative value.
                    try:
                        value = abs(float(value))
                    except (TypeError, ValueError):
                        pass
                variable.set(value)
        self.include_Time.set(1)

    def _load_auto_configuration(self):
        try:
            self._apply_configuration(load_configuration(self.config_path))
        except (OSError, ValueError, ConfigurationError) as exc:
            self.statusbar.configure(bg='red')
            self.statusMessage.set("Configuração inválida; usando padrões: %s" % exc)
            debug_message(traceback.format_exc())

    def _save_configuration(self, show_status=False):
        try:
            save_configuration(self.config_path, self._configuration_values())
            if show_status:
                self.statusbar.configure(bg='white')
                self.statusMessage.set("Configurações salvas: %s" % self.config_path)
        except Exception as exc:
            self.statusbar.configure(bg='red')
            self.statusMessage.set("Não foi possível salvar configurações: %s" % exc)
            debug_message(traceback.format_exc())

    def _schedule_configuration_save(self, *unused):
        if not self._config_ready:
            return
        if self._config_save_after is not None:
            try:
                self.master.after_cancel(self._config_save_after)
            except Exception:
                pass
        self._config_save_after = self.master.after(500, self._autosave_configuration)

    def _autosave_configuration(self):
        self._config_save_after = None
        self._save_configuration()

    def _enable_configuration_autosave(self):
        self._config_ready = True
        for variable in self._configuration_variables().values():
            variable.trace_add("write", self._schedule_configuration_save)

    def Save_Auto_Configuration(self):
        self._save_configuration(show_status=True)

    def Reset_Configuration(self):
        if not message_ask_ok_cancel(
                "Resetar configurações",
                "Restaurar todas as configurações padrão do K40 Whisperer?"):
            return
        self._config_ready = False
        try:
            self._apply_configuration(self._factory_configuration)
        finally:
            self._config_ready = True
        self._save_configuration(show_status=True)
        self.menu_View_Refresh()

    def Write_Config_File(self, event):
        
        config_data = self.WriteConfig()
        config_file = "k40_whisperer.txt"
        configname_full = self.HOME_DIR + "/" + config_file

        current_name = event.widget.winfo_parent()
        win_id = event.widget.nametowidget(current_name)

        if ( os.path.isfile(configname_full) ):
            try:
                win_id.withdraw()
            except:
                pass

            if not message_ask_ok_cancel("Substituir", "Substituir o arquivo de configuração existente?\n"+configname_full):
                try:
                    win_id.deiconify()
                except:
                    pass
                return
        try:
            fout = open(configname_full,'w')
        except:
            self.statusMessage.set("Não foi possível abrir o arquivo para gravação: %s" %(configname_full))
            self.statusbar.configure( bg = 'red' )
            return
        for line in config_data:
            try:
                fout.write(line+'\n')
            except:
                fout.write('(skipping line)\n')
        fout.close
        self.statusMessage.set("Arquivo de configuração salvo: %s" %(configname_full))
        self.statusbar.configure( bg = 'white' )
        try:
            win_id.deiconify()
        except:
            pass

    ################################################################################
    def WriteConfig(self):
        global Zero
        header = []
        header.append('( K40 Whisperer Settings: '+version+' )')
        header.append('( by Scorch - 2019 )')
        header.append("(=========================================================)")
        # BOOL
        header.append('(k40_whisperer_set include_Reng  %s )'  %( int(self.include_Reng.get())  ))
        header.append('(k40_whisperer_set include_Veng  %s )'  %( int(self.include_Veng.get())  ))
        header.append('(k40_whisperer_set include_Vcut  %s )'  %( int(self.include_Vcut.get())  ))
        header.append('(k40_whisperer_set include_Gcde  %s )'  %( int(self.include_Gcde.get())  ))
        header.append('(k40_whisperer_set include_Time  %s )'  %( int(self.include_Time.get())  ))

        header.append('(k40_whisperer_set halftone      %s )'  %( int(self.halftone.get())      ))
        header.append('(k40_whisperer_set HomeUR        %s )'  %( int(self.HomeUR.get())        ))
        header.append('(k40_whisperer_set show_power    %s )'  %( int(self.show_power.get())    ))
        header.append('(k40_whisperer_set show_test     %s )'  %( int(self.show_test.get())     ))
        header.append('(k40_whisperer_set inputCSYS     %s )'  %( int(self.inputCSYS.get())     ))
        header.append('(k40_whisperer_set advanced      %s )'  %( int(self.advanced.get())      ))
        header.append('(k40_whisperer_set mirror        %s )'  %( int(self.mirror.get())        ))
        header.append('(k40_whisperer_set rotate        %s )'  %( int(self.rotate.get())        ))
        header.append('(k40_whisperer_set negate        %s )'  %( int(self.negate.get())        ))
        
        header.append('(k40_whisperer_set engraveUP     %s )'  %( int(self.engraveUP.get())     ))
        header.append('(k40_whisperer_set init_home     %s )'  %( int(self.init_home.get())     ))
        header.append('(k40_whisperer_set post_home     %s )'  %( int(self.post_home.get())     ))
        header.append('(k40_whisperer_set post_beep     %s )'  %( int(self.post_beep.get())     ))
        header.append('(k40_whisperer_set post_disp     %s )'  %( int(self.post_disp.get())     ))
        header.append('(k40_whisperer_set post_exec     %s )'  %( int(self.post_exec.get())     ))
        
        header.append('(k40_whisperer_set pre_pr_crc    %s )'  %( int(self.pre_pr_crc.get())    ))
        header.append('(k40_whisperer_set inside_first  %s )'  %( int(self.inside_first.get())  ))

        header.append('(k40_whisperer_set comb_engrave  %s )'  %( int(self.comb_engrave.get())  ))
        header.append('(k40_whisperer_set comb_vector   %s )'  %( int(self.comb_vector.get())   ))
        header.append('(k40_whisperer_set zoom2image    %s )'  %( int(self.zoom2image.get())    ))
        header.append('(k40_whisperer_set rotary        %s )'  %( int(self.rotary.get())        ))
        header.append('(k40_whisperer_set reduced_mem   %s )'  %( int(self.reduced_mem.get())   ))
        header.append('(k40_whisperer_set wait          %s )'  %( int(self.wait.get())          ))

        header.append('(k40_whisperer_set trace_w_laser %s )'  %( int(self.trace_w_laser.get()) ))

        # STRING.get()
        header.append('(k40_whisperer_set max_power     %s )'  %( self.max_power.get()      ))
        header.append('(k40_whisperer_set board_name    %s )'  %( self.board_name.get()     ))
        header.append('(k40_whisperer_set units         %s )'  %( self.units.get()          ))
        
        header.append('(k40_whisperer_set Reng_feed     %s )'  %( self.Reng_feed.get()      ))
        header.append('(k40_whisperer_set Veng_feed     %s )'  %( self.Veng_feed.get()      ))
        header.append('(k40_whisperer_set Vcut_feed     %s )'  %( self.Vcut_feed.get()      ))

        header.append('(k40_whisperer_set Reng_power    %s )'  %( self.Reng_power.get()    ))
        header.append('(k40_whisperer_set Veng_power    %s )'  %( self.Veng_power.get()    ))
        header.append('(k40_whisperer_set Vcut_power    %s )'  %( self.Vcut_power.get()    ))

        header.append('(k40_whisperer_set jog_step      %s )'  %( self.jog_step.get()       ))

        header.append('(k40_whisperer_set Reng_passes   %s )'  %( self.Reng_passes.get()    ))
        header.append('(k40_whisperer_set Veng_passes   %s )'  %( self.Veng_passes.get()    ))
        header.append('(k40_whisperer_set Vcut_passes   %s )'  %( self.Vcut_passes.get()    ))
        header.append('(k40_whisperer_set Gcde_passes   %s )'  %( self.Gcde_passes.get()    ))

        header.append('(k40_whisperer_set rast_step     %s )'  %( self.rast_step.get()      ))
        header.append('(k40_whisperer_set ht_size       %s )'  %( self.ht_size.get()        ))
        
        header.append('(k40_whisperer_set LaserXsize    %s )'  %( self.LaserXsize.get()     ))
        header.append('(k40_whisperer_set LaserYsize    %s )'  %( self.LaserYsize.get()     ))
        header.append('(k40_whisperer_set LaserXscale   %s )'  %( self.LaserXscale.get()    ))
        header.append('(k40_whisperer_set LaserYscale   %s )'  %( self.LaserYscale.get()    ))
        header.append('(k40_whisperer_set LaserRscale   %s )'  %( self.LaserRscale.get()    ))
        header.append('(k40_whisperer_set rapid_feed   %s )'  %( self.rapid_feed.get()      ))
        
        header.append('(k40_whisperer_set gotoX         %s )'  %( self.gotoX.get()          ))
        header.append('(k40_whisperer_set gotoY         %s )'  %( self.gotoY.get()          ))

        header.append('(k40_whisperer_set bezier_M1     %s )'  %( self.bezier_M1.get()      ))
        header.append('(k40_whisperer_set bezier_M2     %s )'  %( self.bezier_M2.get()      ))
        header.append('(k40_whisperer_set bezier_weight %s )'  %( self.bezier_weight.get()  ))

        header.append('(k40_whisperer_set trace_gap     %s )'  %( self.trace_gap.get()      ))
        header.append('(k40_whisperer_set trace_speed   %s )'  %( self.trace_speed.get()    ))
        header.append('(k40_whisperer_set Trace_power   %s )'  %( self.Trace_power.get()    ))

        header.append('(k40_whisperer_set test_time     %s )'  %( self.test_time.get()      ))
        header.append('(k40_whisperer_set test_power    %s )'  %( self.test_power.get()     ))
        
##        header.append('(k40_whisperer_set unsharp_flag  %s )'  %( int(self.unsharp_flag.get())  ))
##        header.append('(k40_whisperer_set unsharp_r     %s )'  %( self.unsharp_r.get()      ))
##        header.append('(k40_whisperer_set unsharp_p     %s )'  %( self.unsharp_p.get()      ))
##        header.append('(k40_whisperer_set unsharp_t     %s )'  %( self.unsharp_t.get()      ))

        header.append('(k40_whisperer_set t_timeout     %s )'  %( self.t_timeout.get()      ))
        header.append('(k40_whisperer_set n_timeouts    %s )'  %( self.n_timeouts.get()     ))

        header.append('(k40_whisperer_set ink_timeout   %s )'  %( self.ink_timeout.get()    ))

        
        header.append('(k40_whisperer_set designfile    \042%s\042 )' %( self.DESIGN_FILE   ))
        header.append('(k40_whisperer_set inkscape_path \042%s\042 )' %( self.inkscape_path.get() ))
        header.append('(k40_whisperer_set batch_path    \042%s\042 )' %( self.batch_path.get() ))


        self.jog_step
        header.append("(=========================================================)")

        return header
        ######################################################

    def Quit_Click(self, event):
        self.statusMessage.set("Saindo!")
        if getattr(self, "_config_ready", False):
            self._save_configuration()
        self.Release_USB
        root.destroy()

    def mousePanStart(self,event):
        self.panx = event.x
        self.pany = event.y
        self.move_start_x = event.x
        self.move_start_y = event.y
        
    def mousePan(self,event):
        all = self.PreviewCanvas.find_all()
        dx = event.x-self.panx
        dy = event.y-self.pany

        self.PreviewCanvas.move('LaserTag', dx, dy)
        self.lastx = self.lastx + dx
        self.lasty = self.lasty + dy
        self.panx = event.x
        self.pany = event.y
        
    def mousePanStop(self,event):
        Xold = round(self.laserX,3)
        Yold = round(self.laserY,3)

        can_dx = event.x-self.move_start_x
        can_dy = -(event.y-self.move_start_y)
        
        dx = can_dx*self.PlotScale
        dy = can_dy*self.PlotScale
        if self.HomeUR.get():
            dx = -dx
        Xnew,Ynew = self.XY_in_bounds(dx,dy)
        DXmils = round((Xnew - Xold)*1000.0,0)
        DYmils = round((Ynew - Yold)*1000.0,0)
        
        if self.Send_Rapid_Move(DXmils,DYmils):
            self.laserX,self.laserY = Xnew,Ynew
            actual_pixel_dx = (Xnew-Xold)/self.PlotScale
            if self.HomeUR.get():
                actual_pixel_dx = -actual_pixel_dx
            actual_pixel_dy = -(Ynew-Yold)/self.PlotScale
            self.PreviewCanvas.move(
                'LaserTag',
                actual_pixel_dx - (event.x-self.move_start_x),
                actual_pixel_dy - (event.y-self.move_start_y),
            )
            self._refresh_model_projections()
            self._update_position_status()
        else:
            # Undo the visual drag when the hardware move fails.
            self.PreviewCanvas.move(
                'LaserTag',
                -(event.x-self.move_start_x),
                -(event.y-self.move_start_y),
            )

    def right_mousePanStart(self,event):
        self.s_panx = event.x
        self.s_pany = event.y
        self.s_move_start_x = event.x
        self.s_move_start_y = event.y
        
    def right_mousePan(self,event):
        all = self.PreviewCanvas.find_all()
        dx = event.x-self.s_panx
        dy = event.y-self.s_pany

        self.PreviewCanvas.move('LaserDot', dx, dy)
        self.s_lastx = self.lastx + dx
        self.s_lasty = self.lasty + dy
        self.s_panx = event.x
        self.s_pany = event.y
        
    def right_mousePanStop(self,event):
        Xold = round(self.laserX,3)
        Yold = round(self.laserY,3)
        can_dx =   event.x-self.s_move_start_x
        can_dy = -(event.y-self.s_move_start_y)
        
        dx = can_dx*self.PlotScale
        dy = can_dy*self.PlotScale
            
        DX =  round(dx*1000)
        DY =  round(dy*1000)
        self.Move_Arbitrary(DX,DY)
        self.menu_View_Refresh()

    def LASER_Size(self):
        MINX = 0.0
        MAXY = 0.0
        if self.units.get()=="in":
            MAXX =  float(self.LaserXsize.get())
            MINY = -float(self.LaserYsize.get())
        else:
            MAXX =  float(self.LaserXsize.get())/25.4
            MINY = -float(self.LaserYsize.get())/25.4

        return (MAXX-MINX,MAXY-MINY)


    def XY_in_bounds(self,dx_inches,dy_inches, no_size=False):
        MINX = 0.0
        MAXY = 0.0
        if self.units.get()=="in":
            MAXX =  float(self.LaserXsize.get())
            MINY = -float(self.LaserYsize.get())
        else:
            MAXX =  float(self.LaserXsize.get())/25.4
            MINY = -float(self.LaserYsize.get())/25.4

        if (self.inputCSYS.get() and self.RengData.image == None) or no_size:
            xmin,xmax,ymin,ymax = 0.0,0.0,0.0,0.0
        else:
            xmin,xmax,ymin,ymax = self.Get_Design_Bounds()
        
        X = self.laserX + dx_inches
        Y = self.laserY + dy_inches
        ################
        dx=xmax-xmin
        dy=ymax-ymin
        if X < MINX:
            X = MINX
        if X+dx > MAXX:
            X = MAXX-dx
            
        if Y-dy < MINY:
            Y = MINY+dy
        if Y > MAXY:
            Y = MAXY
        ################
        if not no_size:
            XOFF = self.pos_offset[0]/1000.0
            YOFF = self.pos_offset[1]/1000.0
            if X+XOFF < MINX:
                X= X +(MINX-(X+XOFF))
            if X+XOFF > MAXX:
                X= X -((X+XOFF)-MAXX)
            if Y+YOFF < MINY:
                Y= Y + (MINY-(Y+YOFF))
            if Y+YOFF > MAXY:
                Y= Y -((Y+YOFF)-MAXY)
        ################
        X = round(X,3)
        Y = round(Y,3)
        return X,Y

##    def computeAccurateVeng(self):
##        self.update_gui("Optimize vector engrave.") 
##        self.VengData.set_ecoords(self.optimize_paths(self.VengData.ecoords),data_sorted=True)
##        self.refreshTime()
##            
##    def computeAccurateVcut(self):
##        self.update_gui("Optimize vector cut.") 
##        self.VcutData.set_ecoords(self.optimize_paths(self.VcutData.ecoords),data_sorted=True)
##        self.refreshTime()
##
##    def computeAccurateReng(self):
##        self.update_gui("Calculating Raster engrave.")
##        if self.RengData.image != None:        
##            if self.RengData.ecoords == []:
##                self.make_raster_coords()
##        self.RengData.sorted = True 
##        self.refreshTime()


    def format_time(self,time_in_seconds):
        # format the duration from seconds to something human readable
        if time_in_seconds !=None and time_in_seconds >=0 :
            s = round(time_in_seconds)
            m,s=divmod(s,60)
            h,m=divmod(m,60)
            res = ""
            if h > 0:
                res =  "%dh " %(h)
            if m > 0:
                res += "%dm " %(m)
            if h == 0: 
                res += "%ds " %(s)
            #L=len(res)
            #for i in range(L,8):
            #    res =  res+" "
            return res
        else :
            return "?" 

    def refreshTime(self):
        if self.units.get() == 'in':
            factor =  60.0
        else : 
            factor = 25.4

        Raster_eng_feed = float(self.Reng_feed.get()) / factor
        Vector_eng_feed = float(self.Veng_feed.get()) / factor
        Vector_cut_feed = float(self.Vcut_feed.get()) / factor

        Raster_eng_power = float(self.Reng_power.get())
        Vector_eng_power = float(self.Veng_power.get())
        Vector_cut_power = float(self.Vcut_power.get())
        Gcode_power      = float(self.Gcode_power.get())
        
        Raster_eng_passes = float(self.Reng_passes.get())
        Vector_eng_passes = float(self.Veng_passes.get())
        Vector_cut_passes = float(self.Vcut_passes.get())
        Gcode_passes      = float(self.Gcde_passes.get())

        rapid_feed = 100.0 / 25.4   # 100 mm/s move feed to be confirmed

        if self.RengData.rpaths:
            Reng_time=0
        else:
            Reng_time  = None
        Veng_time  = 0
        Vcut_time  = 0
        
        if self.RengData.len!=None:
            # these equations are a terrible hack based on measured raster engraving times
            # to be fixed someday
            if Raster_eng_feed*60.0 <= 300:
                accel_time=8.3264*(Raster_eng_feed*60.0)**(-0.7451)
            else:
                accel_time=2.5913*(Raster_eng_feed*60.0)**(-0.4795)
                
            t_accel = self.RengData.n_scanlines * accel_time
            Reng_time  =  ( (self.RengData.len)/Raster_eng_feed ) * Raster_eng_passes + t_accel
        if self.VengData.len!=None:
            Veng_time  =  (self.VengData.len / Vector_eng_feed + self.VengData.move / rapid_feed) * Vector_eng_passes
        if self.VcutData.len!=None:
            Vcut_time  =  (self.VcutData.len / Vector_cut_feed + self.VcutData.move / rapid_feed) * Vector_cut_passes
            
        Gcode_time =  self.GcodeData.gcode_time * Gcode_passes

        self.Reng_time.set("Gravação raster: %s" %(self.format_time(Reng_time)))
        self.Veng_time.set("Gravação vetorial: %s" %(self.format_time(Veng_time)))
        self.Vcut_time.set("Corte vetorial: %s" %(self.format_time(Vcut_time)))
        self.Gcde_time.set("G-code: %s" %(self.format_time(Gcode_time)))
        
        ##########################################
        cszw = int(self.PreviewCanvas.cget("width"))
        cszh = int(self.PreviewCanvas.cget("height"))
        HUD_vspace = 15
        HUD_X = cszw-5
        HUD_Y = cszh-5

        w = int(self.master.winfo_width())
        h = int(self.master.winfo_height())
        HUD_X2 = w-20
        HUD_Y2 = h-75
        
        self.PreviewCanvas.delete("HUD")
        self.calc_button.place_forget()
        
        if self.GcodeData.ecoords == []:
            self.PreviewCanvas.create_text(HUD_X, HUD_Y             , fill = "red"  ,text =self.Vcut_time.get(), anchor="se",tags="HUD")
            self.PreviewCanvas.create_text(HUD_X, HUD_Y-HUD_vspace  , fill = "blue" ,text =self.Veng_time.get(), anchor="se",tags="HUD")
            
            if (Reng_time==None):
                #try:
                #    self.calc_button.place_forget()
                #except:
                #    pass
                #self.calc_button = Button(self.master,text="Calculate Raster Time", command=self.menu_Calc_Raster_Time)
                self.calc_button.place(x=HUD_X2, y=HUD_Y2, width=120+20, height=17, anchor="se")   
            else:
                self.calc_button.place_forget()
                self.PreviewCanvas.create_text(HUD_X, HUD_Y-HUD_vspace*2, fill = "black",
                                               text =self.Reng_time.get(), anchor="se",tags="HUD")           
        else:
            self.PreviewCanvas.create_text(HUD_X, HUD_Y, fill = "black",text =self.Gcde_time.get(), anchor="se",tags="HUD")
        ##########################################


    def Settings_ReLoad_Click(self, event):
        win_id=self.grab_current()

    def Close_Current_Window_Click(self,event=None):
        current_name = event.widget.winfo_parent()
        win_id = event.widget.nametowidget(current_name)
        win_id.destroy()
        
    # Left Column #
    #############################
    def Entry_Reng_feed_Check(self):
        try:
            value = float(self.Reng_feed.get())
            vfactor=(25.4/60.0)/self.feed_factor()
            low_limit = self.min_raster_speed*vfactor
            if  value < low_limit:
                self.statusMessage.set(" A velocidade deve ser maior ou igual a %f " %(low_limit))
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Reng_feed_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Reng_feed, self.Entry_Reng_feed_Check(), new=1)        
    #############################
    def Entry_Veng_feed_Check(self):
        try:
            value = float(self.Veng_feed.get())
            vfactor=(25.4/60.0)/self.feed_factor()
            low_limit = self.min_vector_speed*vfactor
            if  value < low_limit:
                self.statusMessage.set(" A velocidade deve ser maior ou igual a %f " %(low_limit))
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Veng_feed_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Veng_feed, self.Entry_Veng_feed_Check(), new=1)
    #############################
    def Entry_Vcut_feed_Check(self):
        try:
            value = float(self.Vcut_feed.get())
            vfactor=(25.4/60.0)/self.feed_factor()
            low_limit = self.min_vector_speed*vfactor
            if  value < low_limit:
                self.statusMessage.set(" A velocidade deve ser maior ou igual a %f " %(low_limit))
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Vcut_feed_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Vcut_feed, self.Entry_Vcut_feed_Check(), new=1)


    #Power
        #############################
    def Entry_Reng_power_Check(self):
        try:
            value = float(self.Reng_power.get())
            low_limit  = 0
            high_limit = 1.
            if  value < 0 or value > high_limit:
                self.statusMessage.set(" A fração de potência deve estar entre 0,00 e 1,00 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Reng_power_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Reng_power, self.Entry_Reng_power_Check(), new=1)        
    #############################
    def Entry_Veng_power_Check(self):
        try:
            value = float(self.Veng_power.get())
            low_limit  = 0
            high_limit = 1.
            if  value < 0 or value > high_limit:
                self.statusMessage.set(" A fração de potência deve estar entre 0,00 e 1,00 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Veng_power_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Veng_power, self.Entry_Veng_power_Check(), new=1)
    #############################
    def Entry_Vcut_power_Check(self):
        try:
            value = float(self.Vcut_power.get())
            low_limit  = 0
            high_limit = 1.
            if  value < 0 or value > high_limit:
                self.statusMessage.set(" A fração de potência deve estar entre 0,00 e 1,00 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Vcut_power_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Vcut_power, self.Entry_Vcut_power_Check(), new=1)
        
    #############################
    def Entry_Trace_Power_Check(self):
        try:
            value = float(self.Trace_power.get())
            low_limit  = 0
            high_limit = 1.
            if  value < 0 or value > high_limit:
                self.statusMessage.set(" A fração de potência deve estar entre 0,00 e 1,00 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Trace_Power_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Trace_Power, self.Entry_Trace_Power_Check(), new=1)
    #############################
    def Entry_Gcode_power_Check(self):
        try:
            value = float(self.Gcode_power.get())
            low_limit  = 0
            high_limit = 1.
            if  value < 0 or value > high_limit:
                self.statusMessage.set(" A fração de potência deve estar entre 0,00 e 1,00 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Gcode_power_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Gcode_power, self.Entry_Gcode_power_Check(), new=1)
    #############################
    def Entry_Test_power_Check(self):
        try:
            value = float(self.test_power.get())
            low_limit  = 0
            high_limit = 1.
            if  value < 0 or value > high_limit:
                self.statusMessage.set(" A fração de potência deve estar entre 0,00 e 1,00 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Test_power_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Test_power, self.Entry_Test_power_Check(), new=1)
    #############################
    def Entry_Test_time_Check(self):
        try:
            value = float(self.test_time.get())
            low_limit  = 0
            high_limit = 9999
            if  value < 0 or value > high_limit:
                self.statusMessage.set(" O tempo deve estar entre 0 e 9999 ms ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Test_time_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Test_time, self.Entry_Test_time_Check(), new=1)
    # End power

    #############################
    def Entry_Step_Check(self):
        try:
            value = float(self.jog_step.get())
            if  value <= 0.0:
                self.statusMessage.set(" O passo deve ser maior que 0,0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Step_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Step, self.Entry_Step_Check(), new=1)


    #############################
    def Entry_GoToX_Check(self):
        try:
            value = float(self.gotoX.get())
            if  (value < 0.0) and (not self.HomeUR.get()):
                self.statusMessage.set(" O valor deve ser maior que 0,0 ")
                return 2 # Value is invalid number
            elif (value > 0.0) and self.HomeUR.get():
                self.statusMessage.set(" O valor deve ser menor ou igual a 0,0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_GoToX_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_GoToX, self.Entry_GoToX_Check(), new=1)

    def Format_Position_Entries(self, event=None):
        """Padroniza coordenadas editáveis com três casas decimais."""
        for variable in (self.gotoX, self.gotoY):
            try:
                variable.set("%.3f" % float(variable.get()))
            except:
                pass

    #############################
    def Entry_GoToY_Check(self):
        try:
            value = float(self.gotoY.get())
            if value < 0.0:
                self.statusMessage.set(" O valor de Y deve ser maior ou igual a 0,0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_GoToY_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_GoToY, self.Entry_GoToY_Check(), new=1)
        
    #############################
    def Entry_Rstep_Check(self):
        try:
            value = self.get_raster_step_1000in()
            if  value <= 0 or value > 63:
                self.statusMessage.set(" O passo deve estar entre 0,001 e 0,063 pol")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Rstep_Callback(self, varName, index, mode):
        self.RengData.reset_path()
        self.refreshTime()
        self.entry_set(self.Entry_Rstep, self.Entry_Rstep_Check(), new=1)

##    #############################
##    def Entry_Unsharp_Radius_Check(self):
##        try:
##            value = float(self.unsharp_r.get())
##            if  value <= 0:
##                self.statusMessage.set(" Radius should be greater than zero.")
##                return 2 # Value is invalid number
##        except:
##            return 3     # Value not a number
##        self.menu_View_Refresh_Callback()
##        return 0         # Value is a valid number
##    def Entry_Unsharp_Radius_Callback(self, varName, index, mode):
##        self.entry_set(self.Entry_Unsharp_Radius, self.Entry_Unsharp_Radius_Check(), new=1)
##        
##
##    #############################
##    def Entry_Unsharp_Percent_Check(self):
##        try:
##            value = float(self.unsharp_p.get())
##            if  value <= 0:
##                self.statusMessage.set(" Percent should be greater than zero.")
##                return 2 # Value is invalid number
##        except:
##            return 3     # Value not a number
##        self.menu_View_Refresh_Callback()
##        return 0         # Value is a valid number
##    def Entry_Unsharp_Percent_Callback(self, varName, index, mode):
##        self.entry_set(self.Entry_Unsharp_Percent, self.Entry_Unsharp_Percent_Check(), new=1)
##        
##    #############################
##    def Entry_Unsharp_Threshold_Check(self):
##        try:
##            value = float(self.unsharp_t.get())
##            if  value < 0:
##                self.statusMessage.set(" Threshold should be greater than or equal to zero.")
##                return 2 # Value is invalid number
##        except:
##            return 3     # Value not a number
##        self.menu_View_Refresh_Callback()
##        return 0         # Value is a valid number
##    def Entry_Unsharp_Threshold_Callback(self, varName, index, mode):
##        self.entry_set(self.Entry_Unsharp_Threshold, self.Entry_Unsharp_Threshold_Check(), new=1)
 
    #############################
    # End Left Column #
    #############################
    def bezier_weight_Callback(self, varName=None, index=None, mode=None):
        self.Reset_RasterPath_and_Update_Time()
        self.bezier_plot()
        
    def bezier_M1_Callback(self, varName=None, index=None, mode=None):
        self.Reset_RasterPath_and_Update_Time()
        self.bezier_plot()

    def bezier_M2_Callback(self, varName=None, index=None, mode=None):
        self.Reset_RasterPath_and_Update_Time()
        self.bezier_plot()

    def bezier_plot(self):
        self.BezierCanvas.delete('bez')

        #self.BezierCanvas.create_line( 5,260-0,260,260-255,fill="black", capstyle="round", width = 2, tags='bez')
        M1 = float(self.bezier_M1.get())
        M2 = float(self.bezier_M2.get())
        w  = float(self.bezier_weight.get())
        num = 10
        x,y = self.generate_bezier(M1,M2,w,n=num)
        for i in range(0,num):
            self.BezierCanvas.create_line( 5+x[i],260-y[i],5+x[i+1],260-y[i+1],fill="black", \
                                           capstyle="round", width = 2, tags='bez')
        self.BezierCanvas.create_text(128, 0, text="Output Level vs. Input Level",anchor="n", tags='bez')


    #############################
    def Entry_Ink_Timeout_Check(self):
        try:
            value = float(self.ink_timeout.get())
            if  value < 0.0:
                self.statusMessage.set(" O tempo limite deve ser igual ou maior que 0")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Ink_Timeout_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Ink_Timeout,self.Entry_Ink_Timeout_Check(), new=1)
        
     
    #############################
    def Entry_Timeout_Check(self):
        try:
            value = float(self.t_timeout.get())
            if  value <= 0.0:
                self.statusMessage.set(" O tempo limite deve ser maior que 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Timeout_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Timeout,self.Entry_Timeout_Check(), new=1)

    #############################
    def Entry_N_Timeouts_Check(self):
        try:
            value = float(self.n_timeouts.get())
            if  value <= 0.0:
                self.statusMessage.set(" O número de tentativas de comunicação deve ser maior que zero ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_N_Timeouts_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_N_Timeouts,self.Entry_N_Timeouts_Check(), new=1)
    
    #############################
    def Entry_N_EGV_Passes_Check(self):
        try:
            value = int(self.n_egv_passes.get())
            if  value < 1:
                self.statusMessage.set(" O número de passadas EGV deve ser 1 ou maior")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_N_EGV_Passes_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_N_EGV_Passes,self.Entry_N_EGV_Passes_Check(), new=1)
        
    #############################
    def Entry_Laser_Area_Width_Check(self):
        try:
            value = float(self.LaserXsize.get())
            if  value <= 0.0:
                self.statusMessage.set(" A largura deve ser maior que 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Laser_Area_Width_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Laser_Area_Width,self.Entry_Laser_Area_Width_Check(), new=1)

    #############################
    def Entry_Max_Power_Check(self):
        try:
            value = float(self.max_power.get())
            if  value < 0.0 or value > 100.0:
                self.statusMessage.set(" A potência máxima deve estar entre 0% e 100% ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Max_Power_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Max_Power,self.Entry_Max_Power_Check(), new=1)

    #############################
    def Entry_Laser_Area_Height_Check(self):
        try:
            value = float(self.LaserYsize.get())
            if  value <= 0.0:
                self.statusMessage.set(" A altura deve ser maior que 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Laser_Area_Height_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Laser_Area_Height,self.Entry_Laser_Area_Height_Check(), new=1)


    #############################
    def Entry_Laser_X_Scale_Check(self):
        try:
            value = float(self.LaserXscale.get())
            if  value <= 0.0:
                self.statusMessage.set(" A escala horizontal deve ser maior que zero ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.Reset_RasterPath_and_Update_Time()
        return 0         # Value is a valid number
    def Entry_Laser_X_Scale_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Laser_X_Scale,self.Entry_Laser_X_Scale_Check(), new=1)
    #############################
    def Entry_Laser_Y_Scale_Check(self):
        try:
            value = float(self.LaserYscale.get())
            if  value <= 0.0:
                self.statusMessage.set(" A escala vertical deve ser maior que zero ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.Reset_RasterPath_and_Update_Time()
        return 0         # Value is a valid number
    def Entry_Laser_Y_Scale_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Laser_Y_Scale,self.Entry_Laser_Y_Scale_Check(), new=1)

    #############################
    def Entry_Laser_R_Scale_Check(self):
        try:
            value = float(self.LaserRscale.get())
            if  value <= 0.0:
                self.statusMessage.set(" A escala do rotativo deve ser maior que zero ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.Reset_RasterPath_and_Update_Time()
        return 0         # Value is a valid number
    def Entry_Laser_R_Scale_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Laser_R_Scale,self.Entry_Laser_R_Scale_Check(), new=1)
        
    #############################
    def Entry_Laser_Rapid_Feed_Check(self):
        try:
            value = float(self.rapid_feed.get())
            vfactor=(25.4/60.0)/self.feed_factor()
            low_limit = 1.0*vfactor
            if  value !=0 and value < low_limit:
                self.statusMessage.set(" A velocidade de deslocamento deve ser no mínimo %f, ou zero para usar o padrão " %(low_limit))
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        return 0         # Value is a valid number
    def Entry_Laser_Rapid_Feed_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Laser_Rapid_Feed,self.Entry_Laser_Rapid_Feed_Check(), new=1)

    # Advanced Column #
    #############################
    def Entry_Reng_passes_Check(self):
        try:
            value = int(self.Reng_passes.get())
            if  value < 1:
                self.statusMessage.set(" O número de passadas deve ser maior que 0 ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Reng_passes_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Reng_passes, self.Entry_Reng_passes_Check(), new=1)        
    #############################
    def Entry_Veng_passes_Check(self):
        try:
            value = int(self.Veng_passes.get())
            if  value < 1:
                self.statusMessage.set(" O número de passadas deve ser maior que zero ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Veng_passes_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Veng_passes, self.Entry_Veng_passes_Check(), new=1)
    #############################
    def Entry_Vcut_passes_Check(self):
        try:
            value = int(self.Vcut_passes.get())
            if  value < 1:
                self.statusMessage.set(" O número de passadas deve ser maior que zero ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Vcut_passes_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Vcut_passes, self.Entry_Vcut_passes_Check(), new=1)
        
    #############################
    def Entry_Gcde_passes_Check(self):
        try:
            value = int(self.Gcde_passes.get())
            if  value < 1:
                self.statusMessage.set(" O número de passadas deve ser maior que zero ")
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Gcde_passes_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Gcde_passes, self.Entry_Gcde_passes_Check(), new=1)
        
    #############################

    def Entry_Trace_Gap_Check(self):
        try:
            value = float(self.trace_gap.get())
        except:
            return 3     # Value not a number
        self.menu_View_Refresh()
        return 0         # Value is a valid number
    def Entry_Trace_Gap_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Trace_Gap, self.Entry_Trace_Gap_Check(), new=1)
        
    #############################

    def Entry_Trace_Speed_Check(self):
        try:
            value = float(self.trace_speed.get())
            vfactor=(25.4/60.0)/self.feed_factor()
            low_limit = self.min_vector_speed*vfactor
            if  value < low_limit:
                self.statusMessage.set(" A velocidade deve ser maior ou igual a %f " %(low_limit))
                return 2 # Value is invalid number
        except:
            return 3     # Value not a number
        self.refreshTime()
        return 0         # Value is a valid number
    def Entry_Trace_Speed_Callback(self, varName, index, mode):
        self.entry_set(self.Entry_Trace_Speed, self.Entry_Trace_Speed_Check(), new=1)
        
    #############################
    def Inkscape_Path_Click(self, event):
        self.Inkscape_Path_Message()
        win_id=self.grab_current()
        newfontdir = askopenfilename(filetypes=[("Executable Files",("inkscape.exe","*inkscape*")),\
                                                ("All Files","*")],\
                                                 initialdir=self.inkscape_path.get())
        if newfontdir != "" and newfontdir != ():
            if type(newfontdir) is not str:
                newfontdir = newfontdir.encode("utf-8")
            self.inkscape_path.set(newfontdir)
            
        try:
            win_id.withdraw()
            win_id.deiconify()
        except:
            pass

    def Inkscape_Path_Message(self, event=None):
        if self.inkscape_warning == False:
            self.inkscape_warning = True
            msg1 = "Atenção:"
            msg2 = "Na maioria dos casos, deixe o campo 'Executável do Inkscape' em branco. "
            msg3 = "O K40 Whisperer localizará o Inkscape em um dos locais padrão após a instalação."
            message_box(msg1, msg2+msg3)
            
            
    def Entry_units_var_Callback(self):
        if (self.units.get() == 'in') and (self.funits.get()=='mm/s'):
            self.funits.set('in/min')
            self.funits_label.set('Speed\nin/min')
            self.Scale_Linear_Inputs('in')
        elif (self.units.get() == 'mm') and (self.funits.get()=='in/min'):
            self.funits.set('mm/s')
            self.funits_label.set('Speed\nmm/s')
            self.Scale_Linear_Inputs('mm')
            
    def Scale_Linear_Inputs(self, new_units=None):
        if new_units=='in':
            self.units_scale = 1.0
            factor  = 1/25.4
            vfactor = 60.0/25.4
        elif new_units=='mm':
            factor  = 25.4
            vfactor = 25.4/60.0
            self.units_scale = 25.4
        else:
            return
        self.LaserXsize.set ( self.Scale_Text_Value('%.2f',self.LaserXsize.get()  ,factor ) )
        self.LaserYsize.set ( self.Scale_Text_Value('%.2f',self.LaserYsize.get()  ,factor ) )
        self.jog_step.set   ( self.Scale_Text_Value('%.3f',self.jog_step.get()    ,factor ) )
        self.gotoX.set      ( self.Scale_Text_Value('%.3f',self.gotoX.get()       ,factor ) )
        self.gotoY.set      ( self.Scale_Text_Value('%.3f',self.gotoY.get()       ,factor ) )
        self.Reng_feed.set  ( self.Scale_Text_Value('%.1f',self.Reng_feed.get()   ,vfactor) )
        self.Veng_feed.set  ( self.Scale_Text_Value('%.1f',self.Veng_feed.get()   ,vfactor) )
        self.Vcut_feed.set  ( self.Scale_Text_Value('%.1f',self.Vcut_feed.get()   ,vfactor) )
        self.trace_speed.set( self.Scale_Text_Value('%.1f',self.trace_speed.get() ,vfactor) )
        self.rapid_feed.set ( self.Scale_Text_Value('%.1f',self.rapid_feed.get()  ,vfactor) )

    def Scale_Text_Value(self,format_txt,Text_Value,factor):
        try:
            return format_txt %(float(Text_Value)*factor )
        except:
            return ''

    def menu_File_Open_Settings_File(self,event=None):
        init_dir = os.path.dirname(self.DESIGN_FILE)
        if ( not os.path.isdir(init_dir) ):
            init_dir = self.HOME_DIR
        fileselect = askopenfilename(filetypes=[("Settings Files","*.txt"),\
                                                ("All Files","*")],\
                                                 initialdir=init_dir)
        if fileselect != '' and fileselect != ():
            self.Open_Settings_File(fileselect)

    def Reduced_Memory_Callback(self, varName, index, mode):
        if self.RengData.image != None:
             self.menu_Reload_Design()
             #print("Reload_Design")
    
    def menu_Reload_Design(self,event=None):
        if self.GUI_Disabled:
            return
        file_full = self.DESIGN_FILE
        file_name = os.path.basename(file_full)
        if ( os.path.isfile(file_full) ):
            filename = file_full
        elif ( os.path.isfile( file_name ) ):
            filename = file_name
        elif ( os.path.isfile( self.HOME_DIR+"/"+file_name ) ):
            filename = self.HOME_DIR+"/"+file_name
        else:
            self.statusMessage.set("Arquivo não encontrado: %s" %(os.path.basename(file_full)) )
            self.statusbar.configure( bg = 'red' ) 
            return
        
        Name, fileExtension = os.path.splitext(filename)
        TYPE=fileExtension.upper()
        if TYPE=='.DXF':
            self.Open_DXF(filename)
            return
        elif TYPE=='.SVG':
            self.Open_SVG(filename)
        elif TYPE=='.EGV':
            self.EGV_Send_Window(filename)
        else:
            self.Open_G_Code(filename)
        self.menu_View_Refresh()
        
        

    def menu_File_Open_Design(self,event=None):
        if self.GUI_Disabled:
            return
        init_dir = os.path.dirname(self.DESIGN_FILE)
        if ( not os.path.isdir(init_dir) ):
            init_dir = self.HOME_DIR

        design_types = ("Design Files", ("*.svg","*.dxf"))
        gcode_types  = ("G-Code Files", ("*.ngc","*.gcode","*.g","*.tap"))
        
        Name, fileExtension = os.path.splitext(self.DESIGN_FILE)
        TYPE=fileExtension.upper()
        if TYPE != '.DXF' and TYPE!='.SVG' and TYPE!='.EGV' and TYPE!='':
            default_types = gcode_types
        else:
            default_types = design_types
        
        fileselect = askopenfilename(filetypes=[default_types,
                                            ("G-Code Files ", ("*.ngc","*.gcode","*.g","*.tap")),\
                                            ("DXF Files ","*.dxf"),\
                                            ("SVG Files ","*.svg"),\
                                            ("All Files ","*"),\
                                            ("Design Files ", ("*.svg","*.dxf"))],\
                                            initialdir=init_dir)

        if fileselect == () or (not os.path.isfile(fileselect)):
            return
            
        Name, fileExtension = os.path.splitext(fileselect)
        self.update_gui("Opening '%s'" % fileselect )
        TYPE=fileExtension.upper()
        if TYPE=='.DXF':
            self.Open_DXF(fileselect)
            return
        elif TYPE=='.SVG':
            self.Open_SVG(fileselect)
        else:
            self.Open_G_Code(fileselect)

            
        self.DESIGN_FILE = fileselect
        self.menu_View_Refresh()
        
    def menu_File_Raster_Engrave(self):
        self.menu_File_save_EGV(operation_type="Raster_Eng")
        
    def menu_File_Vector_Engrave(self):
        self.menu_File_save_EGV(operation_type="Vector_Eng")
        
    def menu_File_Vector_Cut(self):
        self.menu_File_save_EGV(operation_type="Vector_Cut")
        
    def menu_File_G_Code(self):
        self.menu_File_save_EGV(operation_type="Gcode_Cut")
        
    def menu_File_Raster_Vector_Engrave(self):
        self.menu_File_save_EGV(operation_type="Raster_Eng-Vector_Eng")

    def menu_File_Vector_Engrave_Cut(self):
        self.menu_File_save_EGV(operation_type="Vector_Eng-Vector_Cut")

    def menu_File_Raster_Vector_Cut(self):
        self.menu_File_save_EGV(operation_type="Raster_Eng-Vector_Eng-Vector_Cut")

    def menu_File_save_EGV(self,operation_type=None,default_name="out.EGV"):
        if self.display_power:
            msg1 = "Não é possível gravar arquivo EGV com as configurações de potência M3 ativadas"
            self.statusMessage.set(msg1)
            self.statusbar.configure( bg = 'yellow' )
            message_box("Informação:", msg1)
            return
        self.stop[0]=False
        if DEBUG:
            start=time()
        fileName, fileExtension = os.path.splitext(self.DESIGN_FILE)
        init_file=os.path.basename(fileName)
        default_name = init_file+"_"+operation_type
        
        if self.EGV_FILE != None:
            init_dir = os.path.dirname(self.EGV_FILE)
        else:
            init_dir = os.path.dirname(self.DESIGN_FILE)
            
        if ( not os.path.isdir(init_dir) ):
            init_dir = self.HOME_DIR
            
        fileName, fileExtension = os.path.splitext(default_name)
        init_file=os.path.basename(fileName)

        filename = asksaveasfilename(defaultextension='.EGV', \
                                     filetypes=[("EGV File","*.EGV")],\
                                     initialdir=init_dir,\
                                     initialfile= init_file )
        
        if filename != '' and filename != ():

            if operation_type.find("Raster_Eng") > -1:
                self.make_raster_coords()
            else:
                self.statusbar.configure( bg = 'yellow' )
                self.statusMessage.set("Não há dados raster para gravar")
                
            self.send_data(operation_type=operation_type, output_filename=filename)
            self.EGV_FILE = filename
        if DEBUG:
            print("time = %d seconds" %(int(time()-start)))
        self.stop[0]=True
        


    def menu_File_Open_EGV(self):
        init_dir = os.path.dirname(self.DESIGN_FILE)
        if ( not os.path.isdir(init_dir) ):
            init_dir = self.HOME_DIR
        fileselect = askopenfilename(filetypes=[("Engraver Files", ("*.egv","*.EGV")),\
                                                    ("All Files","*")],\
                                                     initialdir=init_dir)
        if fileselect != '' and fileselect != ():
            self.resetPath()
            self.DESIGN_FILE = fileselect
            self.EGV_Send_Window(fileselect)
        
    def Open_EGV(self,filemname,n_passes=1):
        self.stop[0]=False
        EGV_data=[]
        value1 = ""
        value2 = ""
        value3 = ""
        value4 = ""
        data=""
        #value1 and value2 are the absolute y and x starting positions
        #value3 and value4 are the absolute y and x end positions
        with open(filemname) as f:
            while True:
                ## Skip header
                c = f.read(1)
                while c!="%" and c:
                    c = f.read(1)
                ## Read 1st Value
                c = f.read(1)
                while c!="%" and c:
                    value1 = value1 + c
                    c = f.read(1)
                y_start_mils = int(value1) 
                ## Read 2nd Value
                c = f.read(1)
                while c!="%" and c:
                    value2 = value2 + c
                    c = f.read(1)
                x_start_mils = int(value2)   
                ## Read 3rd Value
                c = f.read(1)
                while c!="%" and c:
                    value3 = value3 + c
                    c = f.read(1)
                y_end_mils = int(value3)
                ## Read 4th Value
                c = f.read(1)
                while c!="%" and c:
                    value4 = value4 + c
                    c = f.read(1)
                x_end_mils = int(value4)
                break

            ## Read Data
            while True:
                c = f.read(1)
                if not c:
                    break
                if c=='\n' or c==' ' or c=='\r':
                    pass
                else:
                    data=data+"%c" %c
                    EGV_data.append(ord(c))
                    
        if ( (x_end_mils != 0) or (y_end_mils != 0) ):
            n_passes=1
        else:
            x_start_mils = 0
            y_start_mils = 0

        try:
            self.send_egv_data(EGV_data,n_passes, power_level=None)
        except MemoryError as e:
            msg1 = "Erro de memória:"
            msg2 = "Erro de memória: memória insuficiente."
            self.statusMessage.set(msg2)
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())
            
        except Exception as e:
            #print(traceback.format_exc())
            msg1 = "Envio de dados interrompido: "
            msg2 = "%s" %(e)
            if msg2 == "":
                formatted_lines = traceback.format_exc().splitlines()
            self.statusMessage.set((msg1+msg2).split("\n")[0] )
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())

        #rapid move back to starting position
        dxmils = -(x_end_mils - x_start_mils)
        dymils =   y_end_mils - y_start_mils
        self.Send_Rapid_Move(dxmils,dxmils)
        self.stop[0]=True
        
    def Open_SVG(self,filemname):
        self.resetPath()
        self.SVG_FILE = filemname
        if self.reduced_mem.get():
            self.input_dpi = 500.0
        else:
            self.input_dpi = 1000.0
        svg_reader =  SVG_READER()
        svg_reader.image_dpi = self.input_dpi
        svg_reader.set_inkscape_path(self.inkscape_path.get())
        svg_reader.timout = int(float( self.ink_timeout.get())*60.0) 
        dialog_pxpi    = None
        dialog_viewbox = None
        try:
            try:
                try:
                    svg_reader.parse_svg(self.SVG_FILE)
                    svg_reader.make_paths()
                except SVG_PXPI_EXCEPTION as e:
                    pxpi_dialog = pxpiDialog(root,
                                           self.units.get(),
                                           svg_reader.SVG_Size,
                                           svg_reader.SVG_ViewBox,
                                           svg_reader.SVG_inkscape_version)
                    
                    svg_reader = SVG_READER()
                    svg_reader.image_dpi = self.input_dpi
                    svg_reader.set_inkscape_path(self.inkscape_path.get())
                    svg_reader.timout = int(float( self.ink_timeout.get())*60.0) 
                    if pxpi_dialog.result == None:
                        return
                    
                    dialog_pxpi,dialog_viewbox = pxpi_dialog.result
                    svg_reader.parse_svg(self.SVG_FILE)
                    svg_reader.set_size(dialog_pxpi,dialog_viewbox)
                    svg_reader.make_paths()
                    
            except SVG_TEXT_EXCEPTION as e:
                svg_reader = SVG_READER()
                svg_reader.image_dpi = self.input_dpi
                svg_reader.set_inkscape_path(self.inkscape_path.get())
                svg_reader.timout = int(float( self.ink_timeout.get())*60.0) 
                self.statusMessage.set("Convertendo TEXTO em CAMINHOS.")
                self.master.update()
                svg_reader.parse_svg(self.SVG_FILE)
                if dialog_pxpi != None and dialog_viewbox != None:
                    svg_reader.set_size(dialog_pxpi,dialog_viewbox)
                svg_reader.make_paths(txt2paths=True)
                
        except Exception as e:
            msg1 = "Erro de SVG: "
            msg2 = "%s" %(e)
            self.statusMessage.set((msg1+msg2).split("\n")[0] )
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())
            return
        except:
            self.statusMessage.set("Não foi possível abrir o arquivo SVG: %s" %(filemname))
            debug_message(traceback.format_exc())
            return
        xmax = svg_reader.Xsize/25.4
        ymax = svg_reader.Ysize/25.4
        xmin = 0
        ymin = 0

        self.Design_bounds = (xmin,xmax,ymin,ymax)
            
        ##########################
        ###   Create ECOORDS   ###
        ##########################
        self.VcutData.make_ecoords(svg_reader.cut_lines,scale=1/25.4)
        self.VengData.make_ecoords(svg_reader.eng_lines,scale=1/25.4)

        ##########################
        ###   Load Image       ###
        ##########################
        self.RengData.set_image(svg_reader.raster_PIL)
        
        if (self.RengData.image != None):
            self.wim, self.him = self.RengData.image.size
            self.aspect_ratio =  float(self.wim-1) / float(self.him-1)
            #self.make_raster_coords()
        self.refreshTime()
        margin=0.0625 # A bit of margin to prevent the warningwindow for designs that are close to being within the bounds
        if self.Design_bounds[0] > self.VengData.bounds[0]+margin or\
           self.Design_bounds[0] > self.VcutData.bounds[0]+margin or\
           self.Design_bounds[1] < self.VengData.bounds[1]-margin or\
           self.Design_bounds[1] < self.VcutData.bounds[1]-margin or\
           self.Design_bounds[2] > self.VengData.bounds[2]+margin or\
           self.Design_bounds[2] > self.VcutData.bounds[2]+margin or\
           self.Design_bounds[3] < self.VengData.bounds[3]-margin or\
           self.Design_bounds[3] < self.VcutData.bounds[3]-margin:
            line1 = "Aviso:\n"
            line2 = "Há dados de corte ou gravação vetorial fora dos limites da página SVG.\n\n"
            line3 = "O K40 Whisperer tentará usar todos os dados vetoriais. "
            line4 = "Antes de executar, confirme que os vetores estão dentro da área de trabalho da laser."
            message_box("Aviso", line1+line2+line3+line4)


    #####################################################################
    def make_raster_coords(self):
        if self.RengData.rpaths:
            return True
        try:
            hcoords=[]
            if (self.RengData.image != None and self.RengData.ecoords==[]):
                ecoords=[]
                cutoff=128
                image_temp = self.RengData.image.convert("L")
##                if self.unsharp_flag.get():
##                    from PIL import ImageFilter       
##                    #image_temp = image_temp.filter(UnsharpMask(radius=self.unsharp_r, percent=self.unsharp_p, threshold=self.unsharp_t))
##                    filter = ImageFilter.UnsharpMask()
##                    filter.radius    = float(self.unsharp_r.get())      # radius 3-5 pixels
##                    filter.percent   = int(float(self.unsharp_p.get())) # precent 500%
##                    filter.threshold = int(float(self.unsharp_t.get())) # Threshold 0
##                    image_temp = image_temp.filter(filter)

                if self.negate.get():
                    image_temp = ImageOps.invert(image_temp)
                    
                if self.mirror.get():
                    image_temp = ImageOps.mirror(image_temp)

                if self.rotate.get():
                    #image_temp = image_temp.rotate(90,expand=True)
                    image_temp = self.rotate_raster(image_temp)

                Xscale = float(self.LaserXscale.get())
                Yscale = float(self.LaserYscale.get())    
                if self.rotary.get():
                    Rscale = float(self.LaserRscale.get())
                    Yscale = Yscale*Rscale

                if Xscale != 1.0 or Yscale != 1.0:
                    wim,him = image_temp.size
                    nw = int(wim*Xscale)
                    nh = int(him*Yscale)
                    image_temp = image_temp.resize((nw,nh))

                    
                if self.halftone.get():
                    ht_size_mils =  round( self.input_dpi / float(self.ht_size.get()) ,1)
                    npixels = int( round(ht_size_mils,1) )
                    if npixels == 0:
                        return
                    wim,him = image_temp.size
                    # Convert to Halftoning and save
                    nw=int(wim / npixels)
                    nh=int(him / npixels)
                    image_temp = image_temp.resize((nw,nh))
                    
                    image_temp = self.convert_halftoning(image_temp)
                    image_temp = image_temp.resize((wim,him))
                else:
                    image_temp = image_temp.point(lambda x: 0 if x<128 else 255, '1')
                    
                if DEBUG:
                    image_name = os.path.expanduser("~")+"/IMAGE.png"
                    image_temp.save(image_name,"PNG")

                wim,him = image_temp.size
                #######################################
                Raster_step = int(self.get_raster_step_1000in())
                scanlines = extract_scanlines(
                    image_temp, self.input_dpi, Raster_step, cutoff=cutoff,
                    cancelled=lambda: self.stop[0] == True,
                    progress=lambda percent: (
                        self.statusMessage.set("Criando linhas de varredura: %.1f %%" % percent),
                        self.master.update(),
                    ),
                )
                del image_temp
                ecoords = scanlines.ecoords
                hcoords = scanlines.hull_points
                if hcoords:
                    hcoords = hull2D().convexHullecoords(hcoords)
                self.RengData.set_ecoords(ecoords,data_sorted=True)
                self.RengData.len=scanlines.length_inches
                self.RengData.n_scanlines = scanlines.scanline_count
            #Set Flag indicating raster paths have been calculated    
            self.RengData.rpaths = True
            self.RengData.hull_coords = hcoords
            return True
        
        except MemoryError as e:
            msg1 = "Erro de memória:"
            msg2 = "Erro de memória: memória insuficiente."
            self.statusMessage.set(msg2)
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())
            return False
            
        except Exception as e:
            msg1 = "Criação das coordenadas raster interrompida: "
            msg2 = "%s" %(e)
            self.statusMessage.set((msg1+msg2).split("\n")[0] )
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())
            return False
    #######################################################################

    def _make_raster_coords_worker(self):
        """Calculate raster paths away from Tk's event thread."""
        try:
            if self.RengData.rpaths:
                self.raster_time_queue.put(("complete", None))
                return
            if self.RengData.image is None:
                raise ValueError("Não há preenchimento raster para calcular.")

            image_temp = self.RengData.image.convert("L")
            if self.raster_time_options["negate"]:
                image_temp = ImageOps.invert(image_temp)
            if self.raster_time_options["mirror"]:
                image_temp = ImageOps.mirror(image_temp)
            if self.raster_time_options["rotate"]:
                image_temp = image_temp.rotate(90, expand=True)

            xscale = self.raster_time_options["xscale"]
            yscale = self.raster_time_options["yscale"]
            if xscale != 1.0 or yscale != 1.0:
                width, height = image_temp.size
                image_temp = image_temp.resize(
                    (max(1, int(width*xscale)), max(1, int(height*yscale)))
                )

            if self.raster_time_options["halftone"]:
                pixels = int(round(
                    self.input_dpi/self.raster_time_options["halftone_dpi"], 1
                ))
                if pixels <= 0:
                    raise ValueError("Resolução de meio-tom inválida.")
                width, height = image_temp.size
                image_temp = image_temp.resize(
                    (max(1, int(width/pixels)), max(1, int(height/pixels)))
                )
                image_temp = self.convert_halftoning(
                    image_temp,
                    curve=self.raster_time_options["halftone_curve"],
                    progress=lambda message: self.raster_time_queue.put(
                        ("message", message)
                    ),
                )
                image_temp = image_temp.resize((width, height))
            else:
                image_temp = image_temp.point(lambda value: 0 if value < 128 else 255, '1')

            scanlines = extract_scanlines(
                image_temp, self.input_dpi, self.raster_time_options["raster_step"],
                cutoff=128, cancelled=lambda: self.stop[0],
                progress=lambda percent: self.raster_time_queue.put(("progress", percent)),
                collect_coords=False, collect_hull=False,
            )
            self.raster_time_queue.put(("complete", scanlines))
        except Exception as exc:
            self.raster_time_queue.put(("error", (exc, traceback.format_exc())))

    def _poll_raster_time(self):
        try:
            event, payload = self.raster_time_queue.get_nowait()
        except queue.Empty:
            if self.raster_time_thread is not None:
                self.master.after(50, self._poll_raster_time)
            return

        if event == "progress":
            self.statusMessage.set("Calculando tempo do raster: %.1f %%" % payload)
            self.master.after(10, self._poll_raster_time)
            return
        if event == "message":
            self.statusMessage.set(payload)
            self.master.after(10, self._poll_raster_time)
            return

        self.raster_time_thread = None
        self.raster_time_queue = None
        self.stop[0] = True
        self.set_gui("normal")
        if event == "error":
            error, details = payload
            self.statusbar.configure(bg='red')
            self.statusMessage.set("Falha ao calcular raster: %s" % error)
            debug_message(details)
            return

        if payload is not None:
            self.RengData.len = payload.length_inches
            self.RengData.n_scanlines = payload.scanline_count
        self.refreshTime()
        self.statusbar.configure(bg='white')
        self.statusMessage.set("Tempo estimado calculado: %s" % self.Reng_time.get())


    def rotate_raster(self,image_in):
        wim,him = image_in.size
        im_rotated = Image.new("L", (him, wim), "white")

        image_in_np   = image_in.load()
        im_rotated_np = im_rotated.load()
        
        for i in range(1,him):
            for j in range(1,wim):
                im_rotated_np[i,wim-j] = image_in_np[j,i]
        return im_rotated
    
    def get_raster_step_1000in(self):
        val_in = float(self.rast_step.get())
        value = int(round(val_in*1000.0,1)) 
        return value


    def generate_bezier(self,M1,M2,w,n=100):
        if (M1==M2):
            x1=0
            y1=0
        else:
            x1 = 255*(1-M2)/(M1-M2)
            y1 = M1*x1
        x=[]
        y=[]
        # Calculate Bezier Curve
        for step in range(0,n+1):
            t    = float(step)/float(n)
            Ct   = 1 / ( pow(1-t,2)+2*(1-t)*t*w+pow(t,2) )
            x.append( Ct*( 2*(1-t)*t*w*x1+pow(t,2)*255) )
            y.append( Ct*( 2*(1-t)*t*w*y1+pow(t,2)*255) )
        return x,y

    '''This Example opens an Image and transform the image into halftone.  -Isai B. Cicourel'''
    # Create a Half-tone version of the image
    def convert_halftoning(self, image, curve=None, progress=None):
        image = image.convert('L')
        x_lim, y_lim = image.size
        pixel = image.load()
        
        if curve is None:
            M1 = float(self.bezier_M1.get())
            M2 = float(self.bezier_M2.get())
            w = float(self.bezier_weight.get())
        else:
            M1, M2, w = curve
        
        if w > 0:
            x,y = self.generate_bezier(M1,M2,w)
            
            interp = interpolate(x, y) # Set up interpolate class
            val_map=[]
            # Map Bezier Curve to values between 0 and 255
            for val in range(0,256):
                val_out = int(round(interp[val])) # Get the interpolated value at each value
                val_map.append(val_out)
            # Adjust image
            timestamp=0
            for y in range(1, y_lim):
                stamp=int(3*time()) #update every 1/3 of a second
                if (stamp != timestamp):
                    timestamp=stamp #interlock
                    message = "Ajustando a intensidade da imagem: %.1f %%" % ((100.0*y)/y_lim)
                    if progress is None:
                        self.statusMessage.set(message)
                        self.master.update()
                    else:
                        progress(message)
                for x in range(1, x_lim):
                    pixel[x, y] = val_map[ pixel[x, y] ]

        if progress is None:
            self.statusMessage.set("Criando imagem em meio-tom.")
            self.master.update()
        else:
            progress("Criando imagem em meio-tom.")
        image = image.convert('1')
        return image

    #######################################################################

    def gcode_error_message(self,message):
        error_report = Toplevel(width=525,height=60)
        error_report.title("Erros e avisos na leitura do G-code")
        error_report.iconname("G-Code Errors")
        error_report.grab_set()
        return_value =  StringVar()
        return_value.set("none")


        def Close_Click(event):
            return_value.set("close")
            error_report.destroy()
            
        #Text Box
        Error_Frame = Frame(error_report)
        scrollbar = Scrollbar(Error_Frame, orient=VERTICAL)
        Error_Text = Text(Error_Frame, width="80", height="20",yscrollcommand=scrollbar.set,bg='white')
        for line in message:
            Error_Text.insert(END,line+"\n")
        scrollbar.config(command=Error_Text.yview)
        scrollbar.pack(side=RIGHT,fill=Y)
        #End Text Box

        Button_Frame = Frame(error_report)
        close_button = Button(Button_Frame,text=" Close ")
        close_button.bind("<ButtonRelease-1>", Close_Click)
        close_button.pack(side=RIGHT,fill=X)
        
        Error_Text.pack(side=LEFT,fill=BOTH,expand=1)
        Button_Frame.pack(side=BOTTOM)
        Error_Frame.pack(side=LEFT,fill=BOTH,expand=1)
        
        root.wait_window(error_report)
        return return_value.get()

    def Open_G_Code(self,filename):
        self.resetPath()
        
        g_rip = G_Code_Rip()
        try:
            MSG = g_rip.Read_G_Code(filename, XYarc2line = True, arc_angle=2, units="in", Accuracy="")
            Error_Text = ""
            if MSG!=[]:
                self.gcode_error_message(MSG)

        #except StandardError as e:
        except Exception as e:
            msg1 = "Falha ao carregar G-code: "
            msg2 = "Arquivo: %s" %(filename)
            msg3 = "%s" %(e)
            self.statusMessage.set((msg1+msg3).split("\n")[0] )
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, "%s\n%s" %(msg2,msg3))
            debug_message(traceback.format_exc())

            
        ecoords= g_rip.generate_laser_paths(g_rip.g_code_data)
        self.GcodeData.set_ecoords(ecoords,data_sorted=True)
        self.Design_bounds = self.GcodeData.bounds

        
    def Open_DXF(self,filemname):
        if self.dxf_import_thread is not None and self.dxf_import_thread.is_alive():
            self.statusMessage.set("Já existe uma importação DXF em andamento.")
            return

        self.dxf_import_queue = queue.Queue()
        self.dxf_import_cancel = threading.Event()
        self.set_gui("disabled")
        self.statusbar.configure(bg='#f0ad4e')
        self.statusMessage.set("Iniciando importação DXF...")
        self.import_progress.configure(mode="indeterminate", maximum=100, value=0)
        self.import_progress.pack(anchor=SW, fill=X, side=BOTTOM, padx=2, pady=(1, 0))
        self.import_progress.start(12)
        self.dxf_progress_indeterminate = True
        # Keep a resolution-independent working source, as already done for
        # SVG. The configured raster step selects scanlines later and remains
        # independent from the number of passes.
        raster_dpi = 500.0 if self.reduced_mem.get() else 1000.0

        def request_from_ui(kind):
            request = {"kind": kind, "event": threading.Event(), "value": None}
            self.dxf_import_queue.put(("request", request))
            while not request["event"].wait(0.1):
                if self.dxf_import_cancel.is_set():
                    from k40core.importing import ImportCancelled
                    raise ImportCancelled("Importação cancelada pelo usuário.")
            return request["value"]

        def worker():
            try:
                imported = import_dxf(
                    filemname,
                    tolerance_inches=.0005,
                    progress=lambda progress: self.dxf_import_queue.put(("progress", progress)),
                    cancelled=self.dxf_import_cancel.is_set,
                    unit_resolver=lambda: request_from_ui("units"),
                    projection_resolver=lambda: request_from_ui("projection"),
                    raster_dpi=raster_dpi,
                )
                # ECoord is independent from Tk, so the potentially expensive
                # legacy conversion belongs in the worker too.
                from k40core.importing import ImportProgress
                self.dxf_import_queue.put(("progress", ImportProgress(
                    "legacy", message="Preparando geometrias para a interface..."
                )))
                vcut_data = ECoord()
                veng_data = ECoord()
                vcut_data.make_ecoords(imported.cut, scale=1.0)
                veng_data.make_ecoords(imported.engrave, scale=1.0)
                self.dxf_import_queue.put(
                    ("complete", (filemname, imported, vcut_data, veng_data))
                )
            except Exception as exc:
                from k40core.importing import ImportCancelled
                event = "cancelled" if isinstance(exc, ImportCancelled) else "error"
                self.dxf_import_queue.put((event, exc))

        self.dxf_import_thread = threading.Thread(
            target=worker,
            name="k40-dxf-import",
            daemon=True,
        )
        self.dxf_import_thread.start()
        self.master.after(50, self._poll_dxf_import)
        return

    def _poll_dxf_import(self):
        terminal = False
        try:
            while True:
                event, payload = self.dxf_import_queue.get_nowait()
                if event == "progress":
                    message = payload.message or "Importando DXF..."
                    if payload.total:
                        if self.dxf_progress_indeterminate:
                            self.import_progress.stop()
                            self.dxf_progress_indeterminate = False
                        self.import_progress.configure(mode="determinate", maximum=payload.total)
                        self.import_progress["value"] = min(payload.completed, payload.total)
                        percent = 100.0 * payload.completed / payload.total
                        self.statusMessage.set("%s (%.0f%%)" % (message, percent))
                    else:
                        if not self.dxf_progress_indeterminate:
                            self.import_progress.configure(mode="indeterminate", maximum=100, value=0)
                            self.import_progress.start(12)
                            self.dxf_progress_indeterminate = True
                        self.statusMessage.set(message)
                elif event == "request":
                    if payload["kind"] == "units":
                        dialog = UnitsDialog(root)
                    else:
                        dialog = ProjectionDialog(root)
                    payload["value"] = dialog.result
                    payload["event"].set()
                elif event == "complete":
                    filename, imported, vcut_data, veng_data = payload
                    self.resetPath()
                    self.DXF_FILE = filename
                    self.DESIGN_FILE = filename
                    self.VcutData = vcut_data
                    self.VengData = veng_data
                    self.job_document = imported.document
                    if imported.raster_image is not None:
                        self.RengData.set_image(imported.raster_image)
                        self.input_dpi = imported.raster_dpi
                        self.source_raster_dpi = imported.raster_dpi
                        self.wim, self.him = imported.raster_image.size
                        self.aspect_ratio = float(self.wim-1) / float(max(1, self.him-1))
                    self.Design_bounds = imported.bounds
                    self.set_gui("normal")
                    self.statusbar.configure(bg='white')
                    object_count = len(imported.document.vectors) + len(imported.document.fills)
                    self.statusMessage.set("DXF importado: %d objetos" % object_count)
                    self.menu_View_Refresh(incremental=True)
                    if imported.warnings:
                        message_box("Importação de DXF:", "\n".join(imported.warnings))
                    terminal = True
                elif event == "cancelled":
                    self.set_gui("normal")
                    self.statusbar.configure(bg='yellow')
                    self.statusMessage.set("Importação DXF cancelada; o desenho anterior foi preservado.")
                    terminal = True
                elif event == "error":
                    self.set_gui("normal")
                    self.statusbar.configure(bg='red')
                    self.statusMessage.set(str(payload).split("\n")[0])
                    message_box(
                        "Falha ao carregar DXF",
                        "A importação foi interrompida e o desenho anterior foi preservado:\n%s" % payload,
                    )
                    terminal = True
        except queue.Empty:
            pass

        if terminal:
            self.import_progress.stop()
            self.import_progress.pack_forget()
            self.dxf_progress_indeterminate = False
            self.dxf_import_thread = None
            self.dxf_import_queue = None
            self.dxf_import_cancel = None
        elif self.dxf_import_thread is not None:
            self.master.after(50, self._poll_dxf_import)


    def Open_Settings_File(self,filename):
        try:
            fin = open(filename,'r')
        except:
            fmessage("Unable to open file: %s" %(filename))
            return
        
        text_codes=[]
        ident = "k40_whisperer_set"
        for line in fin:
            try:
                if ident in line:
                    # BOOL
                    if "include_Reng"  in line:
                        self.include_Reng.set(line[line.find("include_Reng"):].split()[1])
                    elif "include_Veng"  in line:
                        self.include_Veng.set(line[line.find("include_Veng"):].split()[1])
                    elif "include_Vcut"  in line:
                        self.include_Vcut.set(line[line.find("include_Vcut"):].split()[1])
                    elif "include_Gcde"  in line:
                        self.include_Gcde.set(line[line.find("include_Gcde"):].split()[1])
                    elif "include_Time"  in line:
                        self.include_Time.set(1)
                    elif "halftone"  in line:
                        self.halftone.set(line[line.find("halftone"):].split()[1])
                    elif "negate"  in line:
                        self.negate.set(line[line.find("negate"):].split()[1])
                    elif "HomeUR"  in line:
                        self.HomeUR.set(line[line.find("HomeUR"):].split()[1])
                    elif "show_power"  in line:
                        self.show_power.set(line[line.find("show_power"):].split()[1])
                    elif "show_test"  in line:
                        self.show_test.set(line[line.find("show_test"):].split()[1])
                    elif "inputCSYS"  in line:
                        self.inputCSYS.set(line[line.find("inputCSYS"):].split()[1])
                    elif "advanced"  in line:
                        self.advanced.set(line[line.find("advanced"):].split()[1])
                    elif "mirror"  in line:
                        self.mirror.set(line[line.find("mirror"):].split()[1])
                    elif "rotate"  in line:
                        self.rotate.set(line[line.find("rotate"):].split()[1])
                    elif "engraveUP"  in line:
                        self.engraveUP.set(line[line.find("engraveUP"):].split()[1])
                    elif "init_home"  in line:
                        self.init_home.set(line[line.find("init_home"):].split()[1])
                    elif "post_home"  in line:
                        self.post_home.set(line[line.find("post_home"):].split()[1])
                    elif "post_beep"  in line:
                        self.post_beep.set(line[line.find("post_beep"):].split()[1])
                    elif "post_disp"  in line:
                        self.post_disp.set(line[line.find("post_disp"):].split()[1])
                    elif "post_exec"  in line:
                        self.post_exec.set(line[line.find("post_exec"):].split()[1])
                        
                    elif "pre_pr_crc"  in line:
                        self.pre_pr_crc.set(line[line.find("pre_pr_crc"):].split()[1])
                    elif "inside_first"  in line:
                        self.inside_first.set(line[line.find("inside_first"):].split()[1])
                    elif "comb_engrave"  in line:
                        self.comb_engrave.set(line[line.find("comb_engrave"):].split()[1])
                    elif "comb_vector"  in line:
                        self.comb_vector.set(line[line.find("comb_vector"):].split()[1])
                    elif "zoom2image"  in line:
                        self.zoom2image.set(line[line.find("zoom2image"):].split()[1])

                    elif "rotary"  in line:
                         self.rotary.set(line[line.find("rotary"):].split()[1])
                    elif "reduced_mem"  in line:
                         self.reduced_mem.set(line[line.find("reduced_mem"):].split()[1])
                    elif "wait"  in line:
                         self.wait.set(line[line.find("wait"):].split()[1])

                    elif "trace_w_laser"  in line:
                         self.trace_w_laser.set(line[line.find("trace_w_laser"):].split()[1])
            
                    # STRING.set()
                    elif "board_name" in line:
                        self.board_name.set(line[line.find("board_name"):].split()[1])
                    elif "units"    in line:
                        self.units.set(line[line.find("units"):].split()[1])
                    elif "Reng_feed"    in line:
                         self.Reng_feed .set(line[line.find("Reng_feed"):].split()[1])
                    elif "Veng_feed"    in line:
                         self.Veng_feed .set(line[line.find("Veng_feed"):].split()[1])  
                    elif "Vcut_feed"    in line:
                         self.Vcut_feed.set(line[line.find("Vcut_feed"):].split()[1])

                    elif "max_power"    in line:
                         self.max_power.set(line[line.find("max_power"):].split()[1])  
                    elif "Reng_power"    in line:
                         self.Reng_power .set(line[line.find("Reng_power"):].split()[1])
                    elif "Veng_power"    in line:
                         self.Veng_power .set(line[line.find("Veng_power"):].split()[1])  
                    elif "Vcut_power"    in line:
                         self.Vcut_power.set(line[line.find("Vcut_power"):].split()[1]) 
                    elif "Gcode_power"    in line:
                         self.Gcode_power.set(line[line.find("Gcode_power"):].split()[1])
                         
                    elif "jog_step"    in line:
                         self.jog_step.set(line[line.find("jog_step"):].split()[1])
                         
                    elif "Reng_passes"    in line:
                         self.Reng_passes.set(line[line.find("Reng_passes"):].split()[1])
                    elif "Veng_passes"    in line:
                         self.Veng_passes.set(line[line.find("Veng_passes"):].split()[1])
                    elif "Vcut_passes"    in line:
                         self.Vcut_passes.set(line[line.find("Vcut_passes"):].split()[1])
                    elif "Gcde_passes"    in line:
                         self.Gcde_passes.set(line[line.find("Gcde_passes"):].split()[1])

                    elif "rast_step"    in line:
                         self.rast_step.set(line[line.find("rast_step"):].split()[1])
                    elif "ht_size"    in line:
                         self.ht_size.set(line[line.find("ht_size"):].split()[1])

                    elif "LaserXsize"    in line:
                         self.LaserXsize.set(line[line.find("LaserXsize"):].split()[1])
                    elif "LaserYsize"    in line:
                         self.LaserYsize.set(line[line.find("LaserYsize"):].split()[1])

                    elif "LaserXscale"    in line:
                         self.LaserXscale.set(line[line.find("LaserXscale"):].split()[1])
                    elif "LaserYscale"    in line:
                         self.LaserYscale.set(line[line.find("LaserYscale"):].split()[1])
                    elif "LaserRscale"    in line:
                         self.LaserRscale.set(line[line.find("LaserRscale"):].split()[1])

                    elif "rapid_feed"    in line:
                         self.rapid_feed.set(line[line.find("rapid_feed"):].split()[1])
                         
                    elif "gotoX"    in line:
                         self.gotoX.set(line[line.find("gotoX"):].split()[1])
                    elif "gotoY"    in line:
                         legacy_y = line[line.find("gotoY"):].split()[1]
                         self.gotoY.set(str(abs(float(legacy_y))))

                    elif "bezier_M1"    in line:
                         self.bezier_M1.set(line[line.find("bezier_M1"):].split()[1])
                    elif "bezier_M2"    in line:
                         self.bezier_M2.set(line[line.find("bezier_M2"):].split()[1])
                    elif "bezier_weight"    in line:
                         self.bezier_weight.set(line[line.find("bezier_weight"):].split()[1])
                    elif "trace_gap"    in line:
                         self.trace_gap.set(line[line.find("trace_gap"):].split()[1])
                    elif "trace_speed"    in line:
                         self.trace_speed.set(line[line.find("trace_speed"):].split()[1])
                    elif "Trace_power"    in line:
                         self.Trace_power.set(line[line.find("Trace_power"):].split()[1])

                    elif "test_time"    in line:
                         self.test_time.set(line[line.find("test_time"):].split()[1])
                    elif "test_power"    in line:
                         self.test_power.set(line[line.find("test_power"):].split()[1])               

    ##                elif "unsharp_flag"    in line:
    ##                     self.unsharp_flag.set(line[line.find("unsharp_flag"):].split()[1])
    ##                elif "unsharp_r"    in line:
    ##                     self.unsharp_r.set(line[line.find("unsharp_r"):].split()[1])
    ##                elif "unsharp_p"    in line:
    ##                     self.unsharp_p.set(line[line.find("unsharp_p"):].split()[1])
    ##                elif "unsharp_t"    in line:
    ##                     self.unsharp_t.set(line[line.find("unsharp_t"):].split()[1])
            
                    elif "t_timeout"    in line:
                         self.t_timeout.set(line[line.find("t_timeout"):].split()[1])
                    elif "n_timeouts"    in line:
                         self.n_timeouts.set(line[line.find("n_timeouts"):].split()[1])

                    elif "ink_timeout"    in line:
                         self.ink_timeout.set(line[line.find("ink_timeout"):].split()[1])

                    elif "designfile"    in line:
                           self.DESIGN_FILE=(line[line.find("designfile"):].split("\042")[1])
                    elif "inkscape_path"    in line:
                         self.inkscape_path.set(line[line.find("inkscape_path"):].split("\042")[1])
                    elif "batch_path"    in line:
                         self.batch_path.set(line[line.find("batch_path"):].split("\042")[1])

                         
            except:
                #Ignoring exeptions during reading data from line 
                pass
                     
        fin.close()

        fileName, fileExtension = os.path.splitext(self.DESIGN_FILE)
        init_file=os.path.basename(fileName)
        
        if init_file != "None":
            if ( os.path.isfile(self.DESIGN_FILE) ):
                pass
            else:
                self.statusMessage.set("Arquivo de imagem não encontrado: %s " %(self.DESIGN_FILE))

        if self.units.get() == 'in':
            self.funits.set('in/min')
            self.funits_label.set('Speed\nin/min')
            self.units_scale = 1.0
        else:
            self.units.set('mm')
            self.funits.set('mm/s')
            self.funits_label.set('Speed\nmm/s')
            self.units_scale = 25.4

        temp_name, fileExtension = os.path.splitext(filename)
        file_base=os.path.basename(temp_name)
            
        if self.initComplete == 1:
            self.menu_Mode_Change()
            self.DESIGN_FILE = filename
            
    ##########################################################################
    ##########################################################################
    def menu_File_Save(self):
        settings_data = self.WriteConfig()
        init_dir = os.path.dirname(self.DESIGN_FILE)
        if ( not os.path.isdir(init_dir) ):
            init_dir = self.HOME_DIR
            
        fileName, fileExtension = os.path.splitext(self.DESIGN_FILE)
        init_file=os.path.basename(fileName)

        filename = asksaveasfilename(defaultextension='.txt', \
                                     filetypes=[("Text File","*.txt")],\
                                     initialdir=init_dir,\
                                     initialfile= init_file )

        if filename != '' and filename != ():
            try:
                fout = open(filename,'w')
            except:
                self.statusMessage.set("Não foi possível abrir o arquivo para gravação: %s" %(filename))
                self.statusbar.configure( bg = 'red' )
                return

            for line in settings_data:
                try:
                    fout.write(line+'\n')
                except:
                    fout.write('(skipping line)\n')
                    debug_message(traceback.format_exc())
            fout.close
            self.statusMessage.set("Arquivo salvo: %s" %(filename))
            self.statusbar.configure( bg = 'white' )
        
    def Get_Design_Bounds(self):
        if self.rotate.get():
            ymin =  self.Design_bounds[0]
            ymax =  self.Design_bounds[1]
            xmin = -self.Design_bounds[3]
            xmax = -self.Design_bounds[2]
        else:
            xmin,xmax,ymin,ymax = self.Design_bounds
        return (xmin,xmax,ymin,ymax)
    
    def Move_UL(self,dummy=None):
        xmin,xmax,ymin,ymax = self.Get_Design_Bounds()
        if self.HomeUR.get():
            Xnew = self.laserX + (xmax-xmin)
            DX = round((xmax-xmin)*1000.0)
        else:
            Xnew = self.laserX
            DX = 0
            
        (Xsize,Ysize)=self.LASER_Size()
        if Xnew <= Xsize+.001:
            self.move_head_window_temporary([DX,0.0])
        else:
            pass

    def Move_UR(self,dummy=None):
        xmin,xmax,ymin,ymax = self.Get_Design_Bounds()
        if self.HomeUR.get():
            Xnew = self.laserX
            DX = 0
        else:
            Xnew = self.laserX + (xmax-xmin) 
            DX = round((xmax-xmin)*1000.0)

        (Xsize,Ysize)=self.LASER_Size()
        if Xnew <= Xsize+.001:
            self.move_head_window_temporary([DX,0.0])
        else:
            pass
    
    def Move_LR(self,dummy=None):
        xmin,xmax,ymin,ymax = self.Get_Design_Bounds()
        if self.HomeUR.get():
            Xnew = self.laserX
            DX = 0
        else:
            Xnew = self.laserX + (xmax-xmin) 
            DX = round((xmax-xmin)*1000.0)
            
        Ynew = self.laserY - (ymax-ymin)
        (Xsize,Ysize)=self.LASER_Size()
        if Xnew <= Xsize+.001 and Ynew >= -Ysize-.001:
            DY = round((ymax-ymin)*1000.0)
            self.move_head_window_temporary([DX,-DY])
        else:
            pass
    
    def Move_LL(self,dummy=None):
        xmin,xmax,ymin,ymax = self.Get_Design_Bounds()
        if self.HomeUR.get():
            Xnew = self.laserX + (xmax-xmin)
            DX = round((xmax-xmin)*1000.0)
        else:
            Xnew = self.laserX
            DX = 0
            
        Ynew = self.laserY - (ymax-ymin)
        (Xsize,Ysize)=self.LASER_Size()
        if Xnew <= Xsize+.001 and Ynew >= -Ysize-.001:
            DY = round((ymax-ymin)*1000.0)
            self.move_head_window_temporary([DX,-DY])
        else:
            pass

    def Move_CC(self,dummy=None):
        xmin,xmax,ymin,ymax = self.Get_Design_Bounds()
        if self.HomeUR.get():
            Xnew = self.laserX + (xmax-xmin)/2.0 
            DX = round((xmax-xmin)/2.0*1000.0)
        else:
            Xnew = self.laserX + (xmax-xmin)/2.0 
            DX = round((xmax-xmin)/2.0*1000.0)

            
        Ynew = self.laserY - (ymax-ymin)/2.0
        (Xsize,Ysize)=self.LASER_Size()
        if Xnew <= Xsize+.001 and Ynew >= -Ysize-.001: 
            DY = round((ymax-ymin)/2.0*1000.0)
            self.move_head_window_temporary([DX,-DY])
        else:
            pass

    def Move_Arbitrary(self,MoveX,MoveY,dummy=None):
        if self.GUI_Disabled:
            return
        if self.HomeUR.get():
            DX = -MoveX
        else:
            DX = MoveX
        DY = MoveY
        NewXpos = self.pos_offset[0]+DX
        NewYpos = self.pos_offset[1]+DY
        self.move_head_window_temporary([NewXpos,NewYpos])

    def Move_Arb_Step(self,dx,dy):
        if self.GUI_Disabled:
            return
        if self.units.get()=="in":
            dx_inches = round(dx*1000)
            dy_inches = round(dy*1000)
        else:
            dx_inches = round(dx/25.4*1000)
            dy_inches = round(dy/25.4*1000)
        self.Move_Arbitrary( dx_inches,dy_inches )

    def Move_Arb_Right(self,dummy=None):
        JOG_STEP = float( self.jog_step.get() )
        self.Move_Arb_Step( JOG_STEP,0 )

    def Move_Arb_Left(self,dummy=None):
        JOG_STEP = float( self.jog_step.get() )
        self.Move_Arb_Step( -JOG_STEP,0 )

    def Move_Arb_Up(self,dummy=None):
        JOG_STEP = float( self.jog_step.get() )
        self.Move_Arb_Step( 0,JOG_STEP )

    def Move_Arb_Down(self,dummy=None):
        JOG_STEP = float( self.jog_step.get() )
        self.Move_Arb_Step( 0,-JOG_STEP )

    ####################################################

    def Move_Right(self,dummy=None):
        JOG_STEP = float( self.jog_step.get() )
        self.Rapid_Move( JOG_STEP,0 )

    def Move_Left(self,dummy=None):
        JOG_STEP = float( self.jog_step.get() )
        self.Rapid_Move( -JOG_STEP,0 )

    def Move_Up(self,dummy=None):
        JOG_STEP = float( self.jog_step.get() )
        self.Rapid_Move( 0,JOG_STEP )

    def Move_Down(self,dummy=None):
        JOG_STEP = float( self.jog_step.get() )
        self.Rapid_Move( 0,-JOG_STEP )

    def Rapid_Move(self,dx,dy):
        if self.GUI_Disabled:
            return
        if self.units.get()=="in":
            dx_inches = round(dx,3)
            dy_inches = round(dy,3)
        else:
            dx_inches = round(dx/25.4,3)
            dy_inches = round(dy/25.4,3)

        if (self.HomeUR.get()):
            dx_inches = -dx_inches

        Xnew,Ynew = self.XY_in_bounds(dx_inches,dy_inches)
        dxmils = (Xnew - self.laserX)*1000.0
        dymils = (Ynew - self.laserY)*1000.0

        if self.k40 == None:
            self.laserX  = Xnew
            self.laserY  = Ynew
            self._move_preview_by_anchor_delta(dxmils/1000.0, dymils/1000.0)
        elif self.Send_Rapid_Move(dxmils,dymils):
            self.laserX  = Xnew
            self.laserY  = Ynew
            self._move_preview_by_anchor_delta(dxmils/1000.0, dymils/1000.0)
        

    def Send_Rapid_Move(self,dxmils,dymils):
        try:
            if self.k40 != None:
                Xscale = float(self.LaserXscale.get())
                Yscale = float(self.LaserYscale.get())
                if self.rotary.get():
                    Rscale = float(self.LaserRscale.get())
                    Yscale = Yscale*Rscale
                    
                if Xscale != 1.0 or Yscale != 1.0:    
                    dxmils = int(round(dxmils *Xscale))
                    dymils = int(round(dymils *Yscale))
                self.k40.n_timeouts = 10
                
                if self.rotary.get() and float(self.rapid_feed.get()):
                    self.slow_jog(int(dxmils),int(dymils))
                else:
                    self.k40.rapid_move(int(dxmils),int(dymils))


                return True
            else:
                return True
        #except StandardError as e:
        except Exception as e:
            msg1 = "Falha no movimento rápido: "
            msg2 = "%s" %(e)
            if msg2 == "":
                formatted_lines = traceback.format_exc().splitlines()
            self.statusMessage.set((msg1+msg2).split("\n")[0] )
            self.statusbar.configure( bg = 'red' )
            debug_message(traceback.format_exc())
            return False


    def slow_jog(self,dxmils,dymils):
        if int(dxmils)==0 and int(dymils)==0:
            return
        self.stop[0]=False
        Rapid_data=[]
        Rapid_inst = egv(target=lambda s:Rapid_data.append(s))
        Rapid_feed = float(self.rapid_feed.get())*self.feed_factor()
        Rapid_inst.make_egv_rapid(dxmils,dymils,Feed=Rapid_feed,board_name=self.board_name.get())
        self.send_egv_data(Rapid_data, 1, power_level=None)
        self.stop[0]=True

    def update_gui(self, message=None, bgcolor='white'):
        if message!=None:
            self.statusMessage.set(message)
            self.statusbar.configure( bg = bgcolor )
        self.master.update()
        return True

    def set_gui(self,new_state="normal"):
        if new_state=="normal":
            self.GUI_Disabled=False
        else:
            self.GUI_Disabled=True

        try:
            self.menuBar.entryconfigure("Arquivo", state=new_state)
            self.menuBar.entryconfigure("Visualizar", state=new_state)
            self.menuBar.entryconfigure("Ferramentas", state=new_state)
            self.menuBar.entryconfigure("Configurações", state=new_state)
            self.menuBar.entryconfigure("Ajuda", state=new_state)
            self.PreviewCanvas.configure(state=new_state)
            
            for w in self.master.winfo_children():
                try:
                    w.configure(state=new_state)
                except:
                    pass
            self.Run_Button.configure(state="normal" if new_state == "normal" else "disabled")
            self.Pause_Button.configure(state="normal")
            self.Stop_Button.configure(state="normal")
            self.statusbar.configure(state="normal")
            self.master.update()
        except:
            if DEBUG:
                debug_message(traceback.format_exc())

    def _sync_run_pause_button(self):
        if self.job_running:
            self.Pause_Button.lift()
        else:
            self.Run_Button.lift()

    def _set_preview_mode(self, mode):
        if mode not in ("rectangle", "contour"):
            return
        self.preview_mode.set(mode)
        label = "Retangular" if mode == "rectangle" else "Contorno"
        self.statusbar.configure(bg='white')
        self.statusMessage.set("Modo do preview: %s." % label)

    def Show_Preview_Mode_Menu(self):
        menu = Menu(self.master, tearoff=0)
        menu.add_radiobutton(label="Retangular", variable=self.preview_mode,
                             value="rectangle",
                             command=lambda: self._set_preview_mode("rectangle"))
        menu.add_radiobutton(label="Contorno", variable=self.preview_mode,
                             value="contour",
                             command=lambda: self._set_preview_mode("contour"))
        x = self.Preview_Menu_Button.winfo_rootx()
        y = self.Preview_Menu_Button.winfo_rooty() + self.Preview_Menu_Button.winfo_height()
        try:
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def Run_Boundary_Preview(self):
        if self.GUI_Disabled:
            return
        self.Trace_Eng(trace_mode=self.preview_mode.get())

    def Run_Selected(self):
        """Executa, em ordem segura, apenas os processos marcados na tabela."""
        if self.GUI_Disabled:
            return

        if self.GcodeData.ecoords != []:
            if self.run_Gcde.get():
                self.Gcode_Cut()
            else:
                self.statusbar.configure(bg='yellow')
                self.statusMessage.set("Selecione o processo G-code para executar.")
            return

        selection = (
            bool(self.run_Reng.get()),
            bool(self.run_Veng.get()),
            bool(self.run_Vcut.get()),
        )
        actions = {
            (True,  False, False): self.Raster_Eng,
            (False, True,  False): self.Vector_Eng,
            (False, False, True):  self.Vector_Cut,
            (True,  True,  False): self.Raster_Vector_Eng,
            (False, True,  True):  self.Vector_Eng_Cut,
            (True,  True,  True):  self.Raster_Vector_Cut,
        }

        if selection == (True, False, True):
            self.Raster_Selected_Operations("Raster_Eng+Vector_Cut")
        elif selection in actions:
            actions[selection]()
        else:
            self.statusbar.configure(bg='yellow')
            self.statusMessage.set("Selecione ao menos um processo para executar.")

    def Raster_Selected_Operations(self, operation_type):
        """Prepara raster para combinações selecionadas pela nova tabela."""
        self.Prepare_for_laser_run("Preparando os processos selecionados...")
        try:
            self.make_raster_coords()
            has_raster = "Raster_Eng" in operation_type and self.RengData.ecoords != []
            has_cut = "Vector_Cut" in operation_type and self.VcutData.ecoords != []
            if has_raster or has_cut:
                self.send_data(operation_type)
            else:
                self.statusbar.configure(bg='yellow')
                self.statusMessage.set("Não há dados para os processos selecionados.")
        except Exception as e:
            self.statusbar.configure(bg='red')
            self.statusMessage.set("Preparação dos dados interrompida: %s" % e)
            message_box("Preparação interrompida", "%s" % e)
            debug_message(traceback.format_exc())
        self.Finish_Job()

    def Pause_Job(self, event=None):
        if self.stop[0]:
            self.statusbar.configure(bg='yellow')
            self.statusMessage.set("Não há trabalho em execução para pausar.")
            return
        if self.k40 is None:
            self.statusbar.configure(bg='yellow')
            self.statusMessage.set("A pausa requer uma laser conectada.")
            return
        try:
            self.k40.pause_un_pause()
            self.job_paused = not self.job_paused
            if self.job_paused:
                self.Pause_Button.configure(text="Continuar", image=self.ui_icons["play"], bg="#5bc0de")
                self.statusbar.configure(bg='#f0ad4e')
                self.statusMessage.set("Trabalho pausado.")
            else:
                self.Pause_Button.configure(text="Pausar", image=self.ui_icons["pause"], bg="#f0ad4e")
                self.statusbar.configure(bg='green')
                self.statusMessage.set("Trabalho retomado.")
        except Exception as e:
            self.statusbar.configure(bg='red')
            self.statusMessage.set("Não foi possível pausar: %s" % e)

    def Stop_Job(self, event=None):
        if self.dxf_import_thread is not None and self.dxf_import_thread.is_alive():
            self.dxf_import_cancel.set()
            self.statusbar.configure(bg='yellow')
            self.statusMessage.set("Cancelando importação DXF...")
            return
        if self.stop[0]:
            return
        try:
            if self.k40 is not None and not self.job_paused:
                self.k40.pause_un_pause()
        except:
            debug_message(traceback.format_exc())
        self.stop[0] = True
        self.job_paused = False
        self.Pause_Button.configure(text="Pausar", image=self.ui_icons["pause"], bg="#f0ad4e")
        self.statusbar.configure(bg='red')
        self.statusMessage.set("Interrompendo o trabalho...")

    def Vector_Cut(self, output_filename=None):
        self.Prepare_for_laser_run("Vector Cut: Processing Vector Data.")
        if self.VcutData.ecoords!=[]:
            self.send_data("Vector_Cut", output_filename)
        else:
            self.statusbar.configure( bg = 'yellow' )
            self.statusMessage.set("Não há dados vetoriais para cortar")
        self.Finish_Job()
        
    def Vector_Eng(self, output_filename=None):
        self.Prepare_for_laser_run("Vector Engrave: Processing Vector Data.")
        if self.VengData.ecoords!=[]:
            self.send_data("Vector_Eng", output_filename)
        else:
            self.statusbar.configure( bg = 'yellow' )
            self.statusMessage.set("Não há dados vetoriais para gravar")
        self.Finish_Job()

    def Trace_Eng(self, output_filename=None, trace_mode="contour"):
        self.Prepare_for_laser_run("Boundary Trace: Processing Data.")
        self.trace_coords = self.make_trace_path(trace_mode)

        if self.trace_coords!=[]:
            self.send_data("Trace_Eng", output_filename)
        else:
            self.statusbar.configure( bg = 'yellow' )
            self.statusMessage.set("Não há dados de contorno para seguir")
        self.Finish_Job()

    def Raster_Eng(self, output_filename=None):
        self.Prepare_for_laser_run("Raster Engraving: Processing Image Data.")
        try:
            self.make_raster_coords()
            if self.RengData.ecoords!=[]:
                self.send_data("Raster_Eng", output_filename)
            else:
                self.statusbar.configure( bg = 'yellow' )
                self.statusMessage.set("Não há dados raster para gravar")

        except MemoryError as e:
            msg1 = "Erro de memória:"
            msg2 = "Erro de memória: memória insuficiente."
            self.statusMessage.set(msg2)
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())
            
        except Exception as e:
            msg1 = "Criação dos dados raster interrompida: "
            msg2 = "%s" %(e)
            self.statusMessage.set((msg1+msg2).split("\n")[0] )
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())
        self.Finish_Job()

    def Raster_Vector_Eng(self, output_filename=None):
        self.Prepare_for_laser_run("Raster Engraving: Processing Image and Vector Data.")
        try:
            self.make_raster_coords()
            if self.RengData.ecoords!=[] or self.VengData.ecoords!=[]:
                self.send_data("Raster_Eng+Vector_Eng", output_filename)
            else:
                self.statusbar.configure( bg = 'yellow' )
                self.statusMessage.set("Não há dados para gravar")
        except Exception as e:
            msg1 = "Preparação dos dados interrompida: "
            msg2 = "%s" %(e)
            self.statusMessage.set((msg1+msg2).split("\n")[0] )
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())
        self.Finish_Job()

    def Vector_Eng_Cut(self, output_filename=None):
        self.Prepare_for_laser_run("Vector Cut: Processing Vector Data.")
        if self.VcutData.ecoords!=[] or self.VengData.ecoords!=[]:
            self.send_data("Vector_Eng+Vector_Cut", output_filename)
        else:
            self.statusbar.configure( bg = 'yellow' )
            self.statusMessage.set("Não há dados vetoriais.")
        self.Finish_Job()
        
    def Raster_Vector_Cut(self, output_filename=None):
        self.Prepare_for_laser_run("Raster Engraving: Processing Image and Vector Data.")
        try:
            self.make_raster_coords()
            if self.RengData.ecoords!=[] or self.VengData.ecoords!=[] or self.VcutData.ecoords!=[]:
                self.send_data("Raster_Eng+Vector_Eng+Vector_Cut", output_filename)
            else:
                self.statusbar.configure( bg = 'yellow' )
                self.statusMessage.set("Não há dados para gravar ou cortar")
        except Exception as e:
            msg1 = "Preparação dos dados interrompida: "
            msg2 = "%s" %(e)
            self.statusMessage.set((msg1+msg2).split("\n")[0] )
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())
        self.Finish_Job()
        
    def Gcode_Cut(self, output_filename=None):
        self.Prepare_for_laser_run("G Code Cutting.")
        if self.GcodeData.ecoords!=[]:
            self.send_data("Gcode_Cut", output_filename)
        else:
            self.statusbar.configure( bg = 'yellow' )
            self.statusMessage.set("Não há dados G-code para executar")
        self.Finish_Job()

    def Prepare_for_laser_run(self,msg):
        self.stop[0]=False
        self.job_paused=False
        self.job_running=True
        self.Pause_Button.configure(text="Pausar", image=self.ui_icons["pause"], bg="#f0ad4e")
        self._sync_run_pause_button()
        self.move_head_window_temporary([0,0])
        self.set_gui("disabled")
        self.statusbar.configure( bg = 'green' )
        self.statusMessage.set(msg)
        self.master.update()

    def Finish_Job(self, event=None):
        self.set_gui("normal")
        self.stop[0]=True
        self.job_paused=False
        self.job_running=False
        self.Pause_Button.configure(text="Pausar", image=self.ui_icons["pause"], bg="#f0ad4e")
        self._sync_run_pause_button()
        if self.post_home.get():
            self.Unlock()

        if self.post_beep.get():
            self.master.bell()

        stderr = ''
        stdout = ''
        if self.post_exec.get():
            cmd = [self.batch_path.get()]
            from subprocess import Popen, PIPE
            startupinfo=None
            proc = Popen(cmd, shell=False, stdout=PIPE, stderr=PIPE, stdin=PIPE, startupinfo=startupinfo)
            stdout,stderr = proc.communicate()

        if self.post_disp.get() or stderr != '':
            msg1 = ''
            minutes = floor(self.run_time / 60)
            seconds = self.run_time - minutes*60
            msg2 = "Trabalho concluído.\nTempo de execução = %02d:%02d" %(minutes,seconds)
            if stdout != '':
                msg2=msg2+'\n\nBatch File Output:\n'+stdout
            if stderr != '':
                msg2=msg2+'\n\nBatch File Errors:\n'+stderr
            self.run_time = 0
            message_box(msg1, msg2)


    def make_trace_path(self, mode="contour"):
        my_hull = hull2D()
        if self.inputCSYS.get() and self.RengData.image == None:
            xmin,xmax,ymin,ymax = 0.0,0.0,0.0,0.0
        else:
            xmin,xmax,ymin,ymax = self.Get_Design_Bounds()
            
        startx = xmin
        starty = ymax

        if mode == "rectangle":
            if xmax <= xmin or ymax <= ymin:
                return []
            gap = float(self.trace_gap.get())/self.units_scale
            trace_coords = rectangular_trace((xmin, xmax, ymin, ymax), gap)
            trace_coords, startx, starty = self.scale_vector_coords(
                trace_coords, startx, starty
            )
            return trace_coords

        #######################################
        Vcut_coords = self.VcutData.ecoords
        Veng_coords = self.VengData.ecoords
        Gcode_coords= self.GcodeData.ecoords
        if self.mirror.get() or self.rotate.get():
            Vcut_coords = self.mirror_rotate_vector_coords(Vcut_coords)
            Veng_coords = self.mirror_rotate_vector_coords(Veng_coords)
            Gcode_coords= self.mirror_rotate_vector_coords(Gcode_coords)

        #######################################
        if self.RengData.ecoords==[]:
            if self.stop[0] == True:
                self.stop[0]=False
                self.make_raster_coords()
                self.stop[0]=True
            else:
                self.make_raster_coords()

        RengHullCoords = []
        Xscale = 1/float(self.LaserXscale.get())
        Yscale = 1/float(self.LaserYscale.get())
        if self.rotary.get():
            Rscale = 1/float(self.LaserRscale.get())
            Yscale = Yscale*Rscale
            
        for point in self.RengData.hull_coords:
            RengHullCoords.append([point[0]*Xscale+xmin, point[1]*Yscale, point[2]])
            
        all_coords = []
        all_coords.extend(Vcut_coords)
        all_coords.extend(Veng_coords)
        all_coords.extend(Gcode_coords)
        all_coords.extend(RengHullCoords)

        trace_coords=[]
        if all_coords != []:
            trace_coords = my_hull.convexHullecoords(all_coords)
            gap = float(self.trace_gap.get())/self.units_scale
            trace_coords = self.offset_eccords(trace_coords,gap)

        trace_coords,startx,starty = self.scale_vector_coords(trace_coords,startx,starty)
        return trace_coords

            
    ################################################################################
    def Sort_Paths(self,ecoords,i_loop=2):
        ##########################
        ###   find loop ends   ###
        ##########################
        Lbeg=[]
        Lend=[]
        if len(ecoords)>0:
            Lbeg.append(0)
            loop_old=ecoords[0][i_loop]
            for i in range(1,len(ecoords)):
                loop = ecoords[i][i_loop]
                if loop != loop_old:
                    Lbeg.append(i)
                    Lend.append(i-1)
                loop_old=loop
            Lend.append(i)

        #######################################################
        # Find new order based on distance to next beg or end #
        #######################################################
        order_out = []
        use_beg=0
        if len(ecoords)>0:
            order_out.append([Lbeg[0],Lend[0]])
        inext = 0
        total=len(Lbeg)
        for i in range(total-1):
            if use_beg==1:
                ii=Lbeg.pop(inext)
                Lend.pop(inext)
            else:
                ii=Lend.pop(inext)
                Lbeg.pop(inext)

            Xcur = ecoords[ii][0]
            Ycur = ecoords[ii][1]

            dx = Xcur - ecoords[ Lbeg[0] ][0]
            dy = Ycur - ecoords[ Lbeg[0] ][1]
            min_dist = dx*dx + dy*dy

            dxe = Xcur - ecoords[ Lend[0] ][0]
            dye = Ycur - ecoords[ Lend[0] ][1]
            min_diste = dxe*dxe + dye*dye

            inext=0
            inexte=0
            for j in range(1,len(Lbeg)):
                dx = Xcur - ecoords[ Lbeg[j] ][0]
                dy = Ycur - ecoords[ Lbeg[j] ][1]
                dist = dx*dx + dy*dy
                if dist < min_dist:
                    min_dist=dist
                    inext=j
                ###
                dxe = Xcur - ecoords[ Lend[j] ][0]
                dye = Ycur - ecoords[ Lend[j] ][1]
                diste = dxe*dxe + dye*dye
                if diste < min_diste:
                    min_diste=diste
                    inexte=j
                ###
            if min_diste < min_dist:
                inext=inexte
                order_out.append([Lend[inexte],Lbeg[inexte]])
                use_beg=1
            else:
                order_out.append([Lbeg[inext],Lend[inext]])
                use_beg=0
        ###########################################################
        return order_out
    
    #####################################################
    # determine if a point is inside a given polygon or not
    # Polygon is a list of (x,y) pairs.
    # http://www.ariel.com.au/a/python-point-int-poly.html
    #####################################################
    def point_inside_polygon(self,x,y,poly):
        n = len(poly)
        inside = -1
        p1x = poly[0][0]
        p1y = poly[0][1]
        for i in range(n+1):
            p2x = poly[i%n][0]
            p2y = poly[i%n][1]
            if y > min(p1y,p2y):
                if y <= max(p1y,p2y):
                    if x <= max(p1x,p2x):
                        if p1y != p2y:
                            xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                        if p1x == p2x or x <= xinters:
                            inside = inside * -1
            p1x,p1y = p2x,p2y

        return inside

    def optimize_paths(self,ecoords,inside_check=True):
        order_out = self.Sort_Paths(ecoords)    
        lastx=-999
        lasty=-999
        Acc=0.004
        cuts=[]

        for line in order_out:
            temp=line
            if temp[0] > temp[1]:
                step = -1
            else:
                step = 1

            loop_old = -1
            
            for i in range(temp[0],temp[1]+step,step):
                x1   = ecoords[i][0]
                y1   = ecoords[i][1]
                loop = ecoords[i][2]
                # check and see if we need to move to a new discontinuous start point
                if (loop != loop_old):
                    dx = x1-lastx
                    dy = y1-lasty
                    dist = sqrt(dx*dx + dy*dy)
                    if dist > Acc:
                        cuts.append([[x1,y1]])
                    else:
                        cuts[-1].append([x1,y1])
                else:
                    cuts[-1].append([x1,y1])
                lastx = x1
                lasty = y1
                loop_old = loop

        if inside_check:
            #####################################################
            # For each loop determine if other loops are inside #
            #####################################################
            Nloops=len(cuts)
            self.LoopTree=[]
            for iloop in range(Nloops):
                self.LoopTree.append([])
    ##            CUR_PCT=float(iloop)/Nloops*100.0
    ##            if (not self.batch.get()):
    ##                self.statusMessage.set('Determining Which Side of Loop to Cut: %d of %d' %(iloop+1,Nloops))
    ##                self.master.update()
                ipoly = cuts[iloop]
                ## Check points in other loops (could just check one) ##
                if ipoly != []:
                    for jloop in range(Nloops):
                        if jloop != iloop:
                            inside = 0
                            inside = inside + self.point_inside_polygon(cuts[jloop][0][0],cuts[jloop][0][1],ipoly)
                            if inside > 0:
                                self.LoopTree[iloop].append(jloop)
            #####################################################
            for i in range(Nloops):
                lns=[]
                lns.append(i)
                self.remove_self_references(lns,self.LoopTree[i])

            self.order=[]
            self.loops = list(range(Nloops))
            for i in range(Nloops):
                if self.LoopTree[i]!=[]:
                    self.addlist(self.LoopTree[i])
                    self.LoopTree[i]=[]
                if self.loops[i]!=[]:
                    self.order.append(self.loops[i])
                    self.loops[i]=[]
        #END inside_check
            ecoords_out = []
            for i in self.order:
                line = cuts[i]
                for coord in line:
                    ecoords_out.append([coord[0],coord[1],i])
        #END inside_check
        else:
            ecoords_out = []
            for i in range(len(cuts)):
                line = cuts[i]
                for coord in line:
                    ecoords_out.append([coord[0],coord[1],i])
                    
        return ecoords_out
            
    def remove_self_references(self,loop_numbers,loops):
        for i in range(0,len(loops)):
            for j in range(0,len(loop_numbers)):
                if loops[i]==loop_numbers[j]:
                    loops.pop(i)
                    return
            if self.LoopTree[loops[i]]!=[]:
                loop_numbers.append(loops[i])
                self.remove_self_references(loop_numbers,self.LoopTree[loops[i]])

    def addlist(self,list):
        for i in list:
            try: #this try/except is a bad hack fix to a recursion error. It should be fixed properly later.
                if self.LoopTree[i]!=[]:
                    self.addlist(self.LoopTree[i]) #too many recursions here causes cmp error
                    self.LoopTree[i]=[]
            except:
                pass
            if self.loops[i]!=[]:
                self.order.append(self.loops[i])
                self.loops[i]=[]


    def mirror_rotate_vector_coords(self,coords):
        xmin = self.Design_bounds[0]
        xmax = self.Design_bounds[1]
        coords_rotate_mirror=[]
        
        for i in range(len(coords)):
            coords_rotate_mirror.append(coords[i][:])
            if self.mirror.get():
                if self.inputCSYS.get() and self.RengData.image == None:
                    coords_rotate_mirror[i][0]=-coords_rotate_mirror[i][0]
                else:
                    coords_rotate_mirror[i][0]=xmin+xmax-coords_rotate_mirror[i][0]
                
                
            if self.rotate.get():
                x = coords_rotate_mirror[i][0]
                y = coords_rotate_mirror[i][1]
                coords_rotate_mirror[i][0] = -y
                coords_rotate_mirror[i][1] =  x
                
        return coords_rotate_mirror

    def scale_vector_coords(self,coords,startx,starty):
        
        Xscale = float(self.LaserXscale.get())
        Yscale = float(self.LaserYscale.get())
        if self.rotary.get():
            Rscale = float(self.LaserRscale.get())
            Yscale = Yscale*Rscale

        coords_scale=[]
        if Xscale != 1.0 or Yscale != 1.0:
            for i in range(len(coords)):
                coords_scale.append(coords[i][:])
                x = coords_scale[i][0]
                y = coords_scale[i][1]
                coords_scale[i][0] = x*Xscale
                coords_scale[i][1] = y*Yscale
            scaled_startx = startx*Xscale
            scaled_starty = starty*Yscale
        else:
            coords_scale = coords
            scaled_startx = startx
            scaled_starty = starty

        return coords_scale,scaled_startx,scaled_starty


    def feed_factor(self):
        if self.units.get()=='in':
            feed_factor = 25.4/60.0
        else:
            feed_factor = 1.0
        return feed_factor

  
    def send_data(self,operation_type=None, output_filename=None):
        num_passes=0
        if self.k40 == None and output_filename == None:
            self.statusMessage.set("A máquina laser não foi inicializada...")
            self.statusbar.configure( bg = 'red' ) 
            return
        if output_filename is None:
            try:
                xmin, xmax, ymin, ymax = self.Get_Design_Bounds()
                x_scale = abs(float(self.LaserXscale.get()))
                y_scale = abs(float(self.LaserYscale.get()))
                if self.rotary.get():
                    y_scale *= abs(float(self.LaserRscale.get()))
                width = (xmax - xmin) * x_scale
                height = (ymax - ymin) * y_scale
                machine_width, machine_height = self.LASER_Size()
                anchor_x = self.laserX + self.pos_offset[0] / 1000.0
                anchor_y = self.laserY + self.pos_offset[1] / 1000.0
                job_bounds = placed_job_bounds(
                    width * 25.4,
                    height * 25.4,
                    anchor_x * 25.4,
                    anchor_y * 25.4,
                    home_on_right=bool(self.HomeUR.get()),
                )
                machine_bounds = Bounds(0.0, -machine_height * 25.4,
                                        machine_width * 25.4, 0.0)
                validate_work_area(job_bounds, machine_bounds)
            except (ValueError, WorkAreaError) as exc:
                self.statusMessage.set(str(exc))
                self.statusbar.configure(bg='red')
                message_box("Trabalho fora da área útil", str(exc))
                return
        try:
            feed_factor=self.feed_factor()
            
            if self.inputCSYS.get() and self.RengData.image == None:
                xmin,xmax,ymin,ymax = 0.0,0.0,0.0,0.0
            else:
                xmin,xmax,ymin,ymax = self.Get_Design_Bounds() 
                        
            startx = xmin
            starty = ymax

            if self.HomeUR.get():
                Xscale = float(self.LaserXscale.get())
                FlipXoffset = Xscale*xmin + Xscale*xmax
                if self.rotate.get():
                    startx = -xmin
            else:
                FlipXoffset = None

            if self.rotary.get():
                Rapid_Feed = float(self.rapid_feed.get())*feed_factor
            else:
                Rapid_Feed = 0.0
                
            Raster_Eng_data=[]
            Vector_Eng_data=[]
            Trace_Eng_data=[]
            Vector_Cut_data=[]
            G_code_Cut_data=[]
                        
            if (operation_type.find("Vector_Cut") > -1) and  (self.VcutData.ecoords!=[]):
                Feed_Rate = float(self.Vcut_feed.get())*feed_factor
                self.statusMessage.set("Corte vetorial: determinando a ordem dos cortes...")
                self.master.update()
                if not self.VcutData.sorted and self.inside_first.get():
                    self.VcutData.set_ecoords(self.optimize_paths(self.VcutData.ecoords),data_sorted=True)


##                DEBUG_PLOT=False
##                test_ecoords=self.VcutData.ecoords
##                if DEBUG_PLOT:
##                    import matplotlib.pyplot as plt
##                    plt.ion()
##                    plt.clf()         
##                    X=[]
##                    Y=[]
##                    LOOP_OLD = test_ecoords[0][2]
##                    for i in range(len(test_ecoords)):
##                        LOOP = test_ecoords[i][2]
##                        if LOOP != LOOP_OLD:
##                            plt.plot(X,Y)
##                            plt.pause(.5)
##                            X=[]
##                            Y=[]
##                            LOOP_OLD=LOOP
##                        X.append(test_ecoords[i][0])
##                        Y.append(test_ecoords[i][1])
##                    plt.plot(X,Y)


                self.statusMessage.set("Gerando dados EGV...")
                self.master.update()

                Vcut_coords = self.VcutData.ecoords
                if self.mirror.get() or self.rotate.get():
                    Vcut_coords = self.mirror_rotate_vector_coords(Vcut_coords)

                Vcut_coords,startx,starty = self.scale_vector_coords(Vcut_coords,startx,starty)
                Vector_Cut_egv_inst = egv(target=lambda s:Vector_Cut_data.append(s))   
                Vector_Cut_egv_inst.make_egv_data(
                                                Vcut_coords,                      \
                                                startX=startx,                    \
                                                startY=starty,                    \
                                                Feed = Feed_Rate,                 \
                                                board_name=self.board_name.get(), \
                                                Raster_step = 0,                  \
                                                update_gui=self.update_gui,       \
                                                stop_calc=self.stop,              \
                                                FlipXoffset=FlipXoffset,          \
                                                Rapid_Feed_Rate = Rapid_Feed,     \
                                                use_laser=True
                                                )

            if (operation_type.find("Vector_Eng") > -1) and  (self.VengData.ecoords!=[]):
                Feed_Rate = float(self.Veng_feed.get())*feed_factor
                self.statusMessage.set("Gravação vetorial: determinando a ordem...")
                self.master.update()
                if not self.VengData.sorted and self.inside_first.get():
                    self.VengData.set_ecoords(self.optimize_paths(self.VengData.ecoords,inside_check=False),data_sorted=True)
                self.statusMessage.set("Gerando dados EGV...")
                self.master.update()

                Veng_coords = self.VengData.ecoords
                if self.mirror.get() or self.rotate.get():
                    Veng_coords = self.mirror_rotate_vector_coords(Veng_coords)

                Veng_coords,startx,starty = self.scale_vector_coords(Veng_coords,startx,starty)
                Vector_Eng_egv_inst = egv(target=lambda s:Vector_Eng_data.append(s))
                Vector_Eng_egv_inst.make_egv_data(
                                                Veng_coords,                      \
                                                startX=startx,                    \
                                                startY=starty,                    \
                                                Feed = Feed_Rate,                 \
                                                board_name=self.board_name.get(), \
                                                Raster_step = 0,                  \
                                                update_gui=self.update_gui,       \
                                                stop_calc=self.stop,              \
                                                FlipXoffset=FlipXoffset,          \
                                                Rapid_Feed_Rate = Rapid_Feed,     \
                                                use_laser=True
                                                )


            if (operation_type.find("Trace_Eng") > -1) and (self.trace_coords!=[]):
                Feed_Rate = float(self.trace_speed.get())*feed_factor
                laser_on = self.trace_w_laser.get()
                self.statusMessage.set("Gerando dados EGV...")
                self.master.update()
                Trace_Eng_egv_inst = egv(target=lambda s:Trace_Eng_data.append(s))
                Trace_Eng_egv_inst.make_egv_data(
                                                self.trace_coords,                \
                                                startX=startx,                    \
                                                startY=starty,                    \
                                                Feed = Feed_Rate,                 \
                                                board_name=self.board_name.get(), \
                                                Raster_step = 0,                  \
                                                update_gui=self.update_gui,       \
                                                stop_calc=self.stop,              \
                                                FlipXoffset=FlipXoffset,          \
                                                Rapid_Feed_Rate = Rapid_Feed,     \
                                                use_laser=laser_on
                                                )
                
                
            if (operation_type.find("Raster_Eng") > -1) and  (self.RengData.ecoords!=[]):
                Feed_Rate = float(self.Reng_feed.get())*feed_factor
                Raster_step = self.get_raster_step_1000in()
                if not self.engraveUP.get():
                    Raster_step = -Raster_step
                    
                raster_startx = 0

                Yscale = float(self.LaserYscale.get())
                if self.rotary.get():
                    Rscale = float(self.LaserRscale.get())
                    Yscale = Yscale*Rscale
                raster_starty = Yscale*starty

                self.statusMessage.set("Gerando dados EGV...")
                self.master.update()
                Raster_Eng_egv_inst = egv(target=lambda s:Raster_Eng_data.append(s))
                Raster_Eng_egv_inst.make_egv_data(
                                                self.RengData.ecoords,            \
                                                startX=raster_startx,             \
                                                startY=raster_starty,             \
                                                Feed = Feed_Rate,                 \
                                                board_name=self.board_name.get(), \
                                                Raster_step = Raster_step,        \
                                                update_gui=self.update_gui,       \
                                                stop_calc=self.stop,              \
                                                FlipXoffset=FlipXoffset,          \
                                                Rapid_Feed_Rate = Rapid_Feed,     \
                                                use_laser=True
                                                )
                #print(len(Raster_Eng_data))
                Raster_Eng_data=Raster_Eng_egv_inst.strip_redundant_codes(Raster_Eng_data)
                #print(len(Raster_Eng_data))

            if (operation_type.find("Gcode_Cut") > -1) and (self.GcodeData.ecoords!=[]):
                self.statusMessage.set("Gerando dados EGV...")
                self.master.update()
                Gcode_coords = self.GcodeData.ecoords
                if self.mirror.get() or self.rotate.get():
                    Gcode_coords = self.mirror_rotate_vector_coords(Gcode_coords)

                Gcode_coords,startx,starty = self.scale_vector_coords(Gcode_coords,startx,starty)
                G_code_Cut_egv_inst = egv(target=lambda s:G_code_Cut_data.append(s))
                G_code_Cut_egv_inst.make_egv_data(
                                                Gcode_coords,                     \
                                                startX=startx,                    \
                                                startY=starty,                    \
                                                Feed = None,                      \
                                                board_name=self.board_name.get(), \
                                                Raster_step = 0,                  \
                                                update_gui=self.update_gui,       \
                                                stop_calc=self.stop,              \
                                                FlipXoffset=FlipXoffset,          \
                                                Rapid_Feed_Rate = Rapid_Feed,     \
                                                use_laser=True
                                                )
                
            if self.display_power:
                #########################################################
                ### Send data to laser with power changed in between  ###
                #########################################################
                max_power = float(self.max_power.get())
                if Trace_Eng_data!=[]:
                    data=[]
                    data.append(ord("I"))
                    trace_passes=1
                    for k in range(trace_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(Trace_Eng_data)
                        
                    power_fraction = float(self.Trace_power.get())
                    if power_fraction > 1: power_fraction=0
                    power = power_fraction*max_power
        
                    self.send_egv_data(data, 1, power_level=power)
                    self.menu_View_Refresh()
                        
                if Raster_Eng_data!=[]:
                    data=[]
                    data.append(ord("I"))
                    num_passes = int(float(self.Reng_passes.get()))
                    for k in range(num_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(Raster_Eng_data)
                    power_fraction = float(self.Reng_power.get())
                    if power_fraction > 1: power_fraction=0
                    power = power_fraction*max_power
                    self.send_egv_data(data, 1, power_level=power)
                    self.menu_View_Refresh()

                if Vector_Eng_data!=[]:
                    data=[]
                    data.append(ord("I"))
                    num_passes = int(float(self.Veng_passes.get()))
                    for k in range(num_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(Vector_Eng_data)
                    power_fraction = float(self.Veng_power.get())
                    if power_fraction > 1: power_fraction=0
                    power = power_fraction*max_power
                    self.send_egv_data(data, 1, power_level=power)
                    self.menu_View_Refresh()

                if Vector_Cut_data!=[]:
                    data=[]
                    data.append(ord("I"))
                    num_passes = int(float(self.Vcut_passes.get()))
                    for k in range(num_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(Vector_Cut_data)
                    power_fraction = float(self.Vcut_power.get())
                    if power_fraction > 1: power_fraction=0
                    power = power_fraction*max_power
                    self.send_egv_data(data, 1, power_level=power)
                    self.menu_View_Refresh()

                if G_code_Cut_data!=[]:
                    data=[]
                    data.append(ord("I"))
                    num_passes = int(float(self.Gcde_passes.get()))
                    for k in range(num_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(G_code_Cut_data)
                    power_fraction = float(self.Gcode_power.get())
                    if power_fraction > 1: power_fraction=0
                    power = power_fraction*max_power
                    self.send_egv_data(data, 1, power_level=power)
                    self.menu_View_Refresh()

                #if len(data)< 4:
                #    raise Exception("No laser data was generated.")
                #########################################################
                self.master.update()
                #if output_filename != None:
                #    self.write_egv_to_file(data,output_filename)
                #else:
                #    self.send_egv_data(data, 1, power_level=None)
                #    self.menu_View_Refresh()
                #########################################################
            else:
                #########################################################
                ### Join Resulting Data together for export into file ###
                ### Power settings are not saved to the file          ###
                #########################################################
                data=[]
                data.append(ord("I"))
                if Trace_Eng_data!=[]:
                    trace_passes=1
                    for k in range(trace_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(Trace_Eng_data)
                if Raster_Eng_data!=[]:
                    num_passes = int(float(self.Reng_passes.get()))
                    for k in range(num_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(Raster_Eng_data)
                if Vector_Eng_data!=[]:
                    num_passes = int(float(self.Veng_passes.get()))
                    for k in range(num_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(Vector_Eng_data)
                if Vector_Cut_data!=[]:
                    num_passes = int(float(self.Vcut_passes.get()))
                    for k in range(num_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(Vector_Cut_data)
                if G_code_Cut_data!=[]:
                    num_passes = int(float(self.Gcde_passes.get()))
                    for k in range(num_passes):
                        if len(data)> 4:
                            data[-4]=ord("@")
                        data.extend(G_code_Cut_data)
                if len(data)< 4:
                    raise Exception("No laser data was generated.")
                #########################################################
                self.master.update()
                if output_filename != None:
                    self.write_egv_to_file(data,output_filename)
                else:
                    self.send_egv_data(data, 1, power_level=None)
                    self.menu_View_Refresh()
                #########################################################
                
        except MemoryError as e:
            msg1 = "Erro de memória:"
            msg2 = "Erro de memória: memória insuficiente."
            self.statusMessage.set(msg2)
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())
        
        except Exception as e:
            #print(traceback.format_exc())
            msg1 = "Envio de dados interrompido: "
            msg2 = "%s" %(e)
            if msg2 == "":
                formatted_lines = traceback.format_exc().splitlines()
            self.statusMessage.set((msg1+msg2).split("\n")[0] )
            self.statusbar.configure( bg = 'red' )
            message_box(msg1, msg2)
            debug_message(traceback.format_exc())

    def send_egv_data(self,data,num_passes=1,power_level=None):
        pre_process_CRC        = self.pre_pr_crc.get()
        if self.k40 != None:
            self.k40.timeout       = int(float( self.t_timeout.get()  ))
            self.k40.n_timeouts    = int(float( self.n_timeouts.get() ))
            time_start = time()
            if (power_level != None):
                self.k40.set_PWM_register(power_level)
            self.k40.send_data(data,self.update_gui,self.stop,num_passes,pre_process_CRC, wait_for_laser=self.wait.get())
            self.run_time = time()-time_start
            if DEBUG:
                print(("Elapsed Time: %.6f" %(time()-time_start)))
            
        else:
            self.statusMessage.set("A laser não foi inicializada.")
            self.statusbar.configure( bg = 'yellow' )
            return
        self.menu_View_Refresh()

    def Test_Fire(self):
        time=int(float(self.test_time.get()))
        if time > 1000: time=0
        max_power = float(self.max_power.get())
        power_fraction = float(self.test_power.get())
        if power_fraction > 1: power_fraction=0
        power_level = power_fraction*max_power
        if self.k40 != None:
            try:
                if (time < 1 or power_level == 0):
                    self.k40.set_PWM_register(power_level)
                else:
                    self.k40.pulse_laser(pct_power=power_level, ms=time)
            except Exception as e:
                #print(traceback.format_exc())
                msg1 = "Falha na operação: "
                msg2 = "%s" %(e)
                if msg2 == "":
                    formatted_lines = traceback.format_exc().splitlines()
                self.statusMessage.set((msg1+msg2).split("\n")[0] )
                self.statusbar.configure( bg = 'red' )
                message_box(msg1, msg2)
                debug_message(traceback.format_exc())
        else:
            self.statusMessage.set("A laser não foi inicializada.")
            self.statusbar.configure( bg = 'yellow' )
            return
         
                
    ##########################################################################
    ##########################################################################
    def write_egv_to_file(self,data,fname):
        if len(data) == 0:
            raise Exception("No data available to write to file.")
        try:
            fout = open(fname,'w')
        except:
            raise Exception("Unable to open file ( %s ) for writing." %(fname))
        fout.write("Document type : LHYMICRO-GL file\n")
        fout.write("Creator-Software: K40 Whisperer\n")
        
        fout.write("\n")
        fout.write("%0%0%0%0%")
        for char_val in data:
            char = chr(char_val)
            fout.write("%s" %(char))
            
        #fout.write("\n")
        fout.close
        self.menu_View_Refresh()
        self.statusMessage.set("Dados salvos em: %s" %(fname))
        
    def Home(self, event=None):
        if self.GUI_Disabled:
            return
        if self.k40 != None:
            self.k40.home_position()
        self.laserX  = 0.0
        self.laserY  = 0.0
        self.pos_offset = [0.0,0.0]
        self.menu_View_Refresh()

    def GoTo(self):
        target_x = float(self.gotoX.get())/self.units_scale
        target_y = float(self.gotoY.get())/self.units_scale
        origin_x, origin_y = origin_for_reference(
            target_x, target_y,
            self.pos_offset[0]/1000.0, self.pos_offset[1]/1000.0,
            home_on_right=bool(self.HomeUR.get()),
        )
        # Rapid_Move receives values in the current UI unit and mirrors X for
        # right-hand home internally.
        xpos = (-origin_x if self.HomeUR.get() else origin_x)*self.units_scale
        ypos = origin_y*self.units_scale
        if self.k40 != None:
            self.k40.home_position()
        self.laserX  = 0.0
        self.laserY  = 0.0
        self.Rapid_Move(xpos,ypos)
        self.menu_View_Refresh()  
        
    def Reset(self):
        if self.k40 != None:
            try:
                self.k40.reset_usb()
                self.statusMessage.set("USB redefinido com sucesso")
            except:
                debug_message(traceback.format_exc())
                pass
            
    def Stop(self,event=None):
        if self.stop[0]==True:
            return
        
        if self.k40 != None:
            try:
                self.k40.pause_un_pause()
            except:
                pass

        Cancel_Job = Stop_ResumeDialog(title="Resume or Terminate Laser Job", parent=app)
        if (Cancel_Job.answer):
            self.stop[0]=True
        else:
            if self.k40 != None:
                self.k40.pause_un_pause()

    def Hide_Advanced(self,event=None):
        self.advanced.set(0)
        self.menu_View_Refresh()

    def Set_Connection_Status(self, state):
        states = {
            "no_board": "plug_gray",
            "detected": "plug_yellow",
            "error": "plug_red",
            "connected": "plug_green",
        }
        if state == "disconnected":
            state = "detected" if self.Laser_Board_Detected() else "no_board"
        self.connection_state = state if state in states else "no_board"
        self.Initialize_Button.configure(image=self.ui_icons[states[self.connection_state]])
        self.Connection_Status.place_forget()

    def Laser_Board_Detected(self):
        """Detecta a controladora sem configurá-la ou enviar comandos."""
        try:
            import usb.core
            return usb.core.find(idVendor=0x1a86, idProduct=0x5512) is not None
        except:
            return False

    def Refresh_Connection_Detection(self):
        """Atualiza o estado passivo enquanto não há conexão ou erro ativo."""
        if self.k40 is None and self.connection_state != "error":
            state = "detected" if self.Laser_Board_Detected() else "no_board"
            self.Set_Connection_Status(state)
        try:
            self.master.after(2000, self.Refresh_Connection_Detection)
        except:
            pass

    def Friendly_USB_Error(self, error):
        """Converte falhas técnicas comuns da conexão em orientações PT-BR."""
        detail = str(error).strip()
        normalized = detail.lower()
        if "device not found" in normalized or "no device" in normalized:
            return ("Nenhuma placa da laser foi encontrada. Ligue a máquina, confira o cabo USB "
                    "e aguarde o plug ficar amarelo antes de tentar novamente.")
        if "backend" in normalized or "libusb" in normalized:
            return ("O driver USB da controladora não está disponível. "
                    "Verifique se o driver libusb está instalado para a placa da laser.")
        if "access denied" in normalized or "permission" in normalized:
            return ("O Windows bloqueou o acesso à placa da laser. Feche outros programas que "
                    "possam estar usando a USB e confirme a instalação do driver.")
        if "busy" in normalized or "resource" in normalized:
            return ("A placa da laser está sendo usada por outro programa. Feche o outro software "
                    "de controle e tente conectar novamente.")
        if "endpoint" in normalized:
            return ("A placa foi encontrada, mas o canal de comunicação USB não pôde ser aberto. "
                    "Reconecte o cabo e verifique o driver da controladora.")
        if "timeout" in normalized or "timed out" in normalized:
            return ("A placa não respondeu dentro do tempo esperado. Verifique se a laser está "
                    "ligada e reconecte o cabo USB.")
        if detail:
            return ("Não foi possível estabelecer comunicação com a laser. Verifique a alimentação, "
                    "o cabo USB e o driver da placa. Detalhe técnico: %s" % detail)
        return ("Não foi possível estabelecer comunicação com a laser. Verifique a alimentação, "
                "o cabo USB e o driver da placa.")

    def Release_USB(self):
        if self.k40 != None:
            try:
                self.k40.release_usb()
                self.statusMessage.set("USB liberado com sucesso")
            except:
                debug_message(traceback.format_exc())
                pass
            self.k40=None
        self.Set_Connection_Status("disconnected")
        
    def Initialize_Laser(self,event=None):
        if self.GUI_Disabled:
            return
        self.stop[0]=True
        self.Release_USB()
        self.k40=None
        self.move_head_window_temporary([0.0,0.0])      
        self.k40=K40_CLASS()
        try:
            self.k40.initialize_device()
            self.k40.say_hello()
            if self.init_home.get():
                self.Home()
            else:
                self.Unlock()
            self.Set_Connection_Status("connected")

        except Exception as e:
            error_text = self.Friendly_USB_Error(e)
            self.statusMessage.set(error_text)
            self.statusbar.configure( bg = 'red' )
            self.k40=None
            self.Set_Connection_Status("error")
            message_box("Não foi possível conectar à laser", error_text)
            debug_message(traceback.format_exc())

        except:
            error_text = "Ocorreu uma falha inesperada ao conectar. Confira a alimentação, o cabo USB e o driver da placa."
            self.statusMessage.set(error_text)
            self.statusbar.configure( bg = 'red' )
            self.k40=None
            self.Set_Connection_Status("error")
            message_box("Não foi possível conectar à laser", error_text)
            debug_message(traceback.format_exc())

    def Unfreeze_Laser(self,event=None):
        if self.GUI_Disabled:
            return
        if self.k40 != None:
            try:
                self.k40.unfreeze()
                self.statusMessage.set("Destravamento concluído")
                self.statusbar.configure( bg = 'white' )
            except:
                pass
            
    def Unlock(self,event=None):
        if self.GUI_Disabled:
            return
        if self.k40 != None:
            try:
                self.k40.unlock_rail()
                self.statusMessage.set("Eixos liberados com sucesso")
                self.statusbar.configure( bg = 'white' )
            except:
                self.statusMessage.set("Falha ao liberar os eixos.")
                self.statusbar.configure( bg = 'red' )
                debug_message(traceback.format_exc())
                pass
    
    ##########################################################################
    ##########################################################################
            
    def menu_File_Quit(self):
        if message_ask_ok_cancel("Sair", "Deseja encerrar o programa?"):
            self.Quit_Click(None)

    def Reset_RasterPath_and_Update_Time(self, varName=0, index=0, mode=0):
        self.RengData.reset_path()
        self.refreshTime()

    def View_Refresh_and_Reset_RasterPath(self, varName=0, index=0, mode=0):
        self.RengData.reset_path()
        self.SCALE = 0
        self.menu_View_Refresh()

    def menu_View_inputCSYS_Refresh_Callback(self, varName, index, mode):
        self.move_head_window_temporary([0.0,0.0])
        self.SCALE = 0
        self.menu_View_Refresh()

    def menu_View_Refresh_Callback(self, varName=0, index=0, mode=0):
        self.SCALE = 0
        self.menu_View_Refresh()

        if DEBUG:
            curframe = inspect.currentframe()
            calframe = inspect.getouterframes(curframe, 2)
            print('menu_View_Refresh_Callback called by: %s' %(calframe[1][3]))

    def menu_View_Refresh(self, incremental=False):
        if DEBUG:
            curframe = inspect.currentframe()
            calframe = inspect.getouterframes(curframe, 2)
            print('menu_View_Refresh called by: %s' %(calframe[1][3]))

        try:
            app.master.title(title_text+"   "+ self.DESIGN_FILE)
        except:
            pass
        dummy_event = Event()
        dummy_event.widget=self.master
        self.Master_Configure(dummy_event,1)
        self.Plot_Data(incremental=incremental)
        self._update_position_status()

    def _update_position_status(self):
        xmin,xmax,ymin,ymax = self.Get_Design_Bounds()
        W = xmax-xmin
        H = ymax-ymin

        if self.units.get()=="in":
            X_display = self.laserX + self.pos_offset[0]/1000.0
            Y_display = display_y(self.laserY + self.pos_offset[1]/1000.0)
            W_display = W
            H_display = H
            U_display = self.units.get()
        else:
            X_display = (self.laserX + self.pos_offset[0]/1000.0)*self.units_scale
            Y_display = display_y(
                self.laserY + self.pos_offset[1]/1000.0
            )*self.units_scale
            W_display = W*self.units_scale
            H_display = H*self.units_scale
            U_display = self.units.get()
        if self.HomeUR.get():
            X_display = -X_display

        self.currentX.set("%.3f" % X_display)
        self.currentY.set("%.3f" % Y_display)

        self.statusMessage.set(" Posição atual: X=%.3f Y=%.3f    ( L x A )=( %.3f%s x %.3f%s ) "
                                %(X_display,
                                  Y_display,
                                  W_display,
                                  U_display,
                                  H_display,
                                  U_display))

        self.statusbar.configure( bg = 'white' )

    def _move_preview_by_anchor_delta(self, dx_inches, dy_inches):
        """Translate the rendered job without rebuilding its vector geometry."""
        if self.preview_render_active:
            # Cancel the old batches and rebuild incrementally at the new anchor.
            self.menu_View_Refresh(incremental=True)
            return

        self._move_preview_tag('LaserTag', dx_inches, dy_inches)
        self._refresh_model_projections()
        self._update_position_status()

    def _move_preview_dot_by_offset_delta(self, dx_inches, dy_inches):
        """Translate only the temporary head marker; job geometry stays fixed."""
        self._move_preview_tag('LaserDot', dx_inches, dy_inches)
        self._refresh_model_projections()
        self._update_position_status()

    def _move_preview_tag(self, tag, dx_inches, dy_inches):
        pixel_dx = dx_inches / self.PlotScale
        if self.HomeUR.get():
            pixel_dx = -pixel_dx
        pixel_dy = -dy_inches / self.PlotScale
        self.PreviewCanvas.move(tag, pixel_dx, pixel_dy)
        
    def menu_Inside_First_Callback(self, varName, index, mode):
        if self.GcodeData.ecoords != []:
            if self.VcutData.sorted == True:
                self.menu_Reload_Design()
            elif self.VengData.sorted == True:
                self.menu_Reload_Design()

    def menu_Mode_Change(self):
        dummy_event = Event()
        dummy_event.widget=self.master
        self.Master_Configure(dummy_event,1)

    def menu_Calc_Raster_Time(self,event=None):
        if getattr(self, "raster_time_thread", None) is not None:
            return
        self.include_Time.set(1)
        self.set_gui("disabled")
        self.stop[0]=False
        yscale = float(self.LaserYscale.get())
        if self.rotary.get():
            yscale *= float(self.LaserRscale.get())
        self.raster_time_options = {
            "negate": bool(self.negate.get()),
            "mirror": bool(self.mirror.get()),
            "rotate": bool(self.rotate.get()),
            "xscale": float(self.LaserXscale.get()),
            "yscale": yscale,
            "halftone": bool(self.halftone.get()),
            "halftone_dpi": float(self.ht_size.get()),
            "halftone_curve": (
                float(self.bezier_M1.get()), float(self.bezier_M2.get()),
                float(self.bezier_weight.get()),
            ),
            "raster_step": int(self.get_raster_step_1000in()),
        }
        self.statusbar.configure(bg='#f0ad4e')
        self.statusMessage.set("Calculando tempo do raster...")
        self.raster_time_queue = queue.Queue()
        self.raster_time_thread = threading.Thread(
            target=self._make_raster_coords_worker,
            name="k40-raster-time", daemon=True,
        )
        self.raster_time_thread.start()
        self.master.after(50, self._poll_raster_time)
        

    def menu_Help_About(self):
        application="K40 Whisperer"
        about = "%s Version %s\n\n" %(application,version)
        about = about + "By Scorch.\n"
        about = about + "\163\143\157\162\143\150\100\163\143\157\162"
        about = about + "\143\150\167\157\162\153\163\056\143\157\155\n"
        about = about + "https://www.scorchworks.com/\n\n"
        try:
            python_version = "%d.%d.%d" %(sys.version_info.major,sys.version_info.minor,sys.version_info.micro)
        except:
            python_version = ""
        about = about + "Python "+python_version+" (%d bit)" %(struct.calcsize("P") * 8)
        message_box("Sobre %s" %(application),about)

    def menu_Help_Web(self):
        webbrowser.open_new(r"https://www.scorchworks.com/K40whisperer/k40whisperer.html")

    def menu_Help_Manual(self):
        webbrowser.open_new(r"https://www.scorchworks.com/K40whisperer/k40w_manual.html")

    def KEY_F1(self, event):
        if self.GUI_Disabled:
            return
        self.menu_Help_About()

    def KEY_F2(self, event):
        if self.GUI_Disabled:
            return
        self.GEN_Settings_Window()

    def KEY_F3(self, event):
        if self.GUI_Disabled:
            return
        self.RASTER_Settings_Window()

    def KEY_F4(self, event):
        if self.GUI_Disabled:
            return
        self.ROTARY_Settings_Window()
        self.menu_View_Refresh()

    def KEY_F5(self, event):
        if self.GUI_Disabled:
            return
        self.menu_View_Refresh()

    def KEY_F6(self, event):
        if self.GUI_Disabled:
            return
        self.JOB_Settings_Window()

    def bindConfigure(self, event):
        if not self.initComplete:
            self.initComplete = 1
            self.menu_Mode_Change()

    def Master_Configure(self, event, update=0):
        if event.widget != self.master:
            return
        
        self.display_power = False
        self.display_test  = False
        if (self.board_name.get()=='LASER-M3'):
            if self.show_power.get():
                self.display_power = True
                if self.show_test.get():
                    self.display_test = True    
            
        x = int(self.master.winfo_x())
        y = int(self.master.winfo_y())
        w = int(self.master.winfo_width())
        h = int(self.master.winfo_height())
        if (self.x, self.y) == (-1,-1):
            self.x, self.y = x,y
        if abs(self.w-w)>10 or abs(self.h-h)>10 or update==1:
            ###################################################
            #  Form changed Size (resized) adjust as required #
            ###################################################
            self.w=w
            self.h=h

            if True:                
                # Left Column #
                w_label=90
                w_entry=46
                w_units=52

                x_label_L=10
                x_entry_L=x_label_L+w_label+20-5
                x_units_L=x_entry_L+w_entry+4
                x_power_L=x_units_L+2 #x_entry_L+w_entry+2 +w_entry+2
                # Colunas compactas. A coluna Potência só ocupa espaço quando
                # a placa M3 oferece controle por software.
                x_process=8
                if self.display_power:
                    x_enabled=123
                    x_speed=160
                    x_power_table=211
                    x_pass_entry=262
                    x_color=316
                    w_process=112
                    w_enabled=34
                    w_speed=48
                    w_power=48
                    w_pass=48
                else:
                    x_enabled=130
                    x_speed=172
                    x_power_table=0
                    x_pass_entry=244
                    x_color=310
                    w_process=120
                    w_enabled=38
                    w_speed=68
                    w_power=0
                    w_pass=58

                if self.display_power:
                    self.Header_Speed.configure(text="Velocidade")
                    self.Header_Power.configure(text="Pot.")
                    self.Header_Passes.configure(text="Pass.")
                else:
                    self.Header_Speed.configure(text="Velocidade")
                    self.Header_Passes.configure(text="Passadas")

                standard_button_h=32
                Yloc=10
                self.Initialize_Button.place(x=12, y=Yloc, width=330, height=standard_button_h)
                self.Connection_Status.place_forget()
                Yloc=Yloc+standard_button_h+5
                self.separator1.place(x=8, y=Yloc, width=334, height=1)
                Yloc=Yloc+6

                self.Open_Button.place(x=12, y=Yloc, width=160, height=standard_button_h)
                self.Reload_Button.place(x=174, y=Yloc, width=168, height=standard_button_h)
                Yloc=Yloc+standard_button_h+4
                self.Edit_Button.place(x=12, y=Yloc, width=160, height=standard_button_h)
                self.Array_Button.place(x=174, y=Yloc, width=168, height=standard_button_h)
                if h>=self.pi_mode_height:
                    Yloc=Yloc+standard_button_h+6
                    self.separator5.place(x=8, y=Yloc, width=334, height=1)
                    Yloc=Yloc+6
                    self.Label_Position_Control.place(x=x_label_L, y=Yloc, width=w_label*2, height=21)

                    Yloc=Yloc+22
                    ###########################################################################
                    bsz=40
                    xoffst=0
                    jog_top=Yloc
                    self.UL_Button.place    (x=xoffst+12      ,  y=Yloc, width=bsz, height=bsz)
                    self.Up_Button.place    (x=xoffst+12+bsz  ,  y=Yloc, width=bsz, height=bsz)
                    self.UR_Button.place    (x=xoffst+12+bsz*2,  y=Yloc, width=bsz, height=bsz)
                    Yloc=Yloc+bsz
                    self.Left_Button.place  (x=xoffst+12      ,y=Yloc, width=bsz, height=bsz)
                    self.CC_Button.place    (x=xoffst+12+bsz  ,y=Yloc, width=bsz, height=bsz)
                    self.Right_Button.place (x=xoffst+12+bsz*2,y=Yloc, width=bsz, height=bsz)
                    Yloc=Yloc+bsz
                    self.LL_Button.place    (x=xoffst+12      ,  y=Yloc, width=bsz, height=bsz)
                    self.Down_Button.place  (x=xoffst+12+bsz  ,  y=Yloc, width=bsz, height=bsz)
                    self.LR_Button.place    (x=xoffst+12+bsz*2,  y=Yloc, width=bsz, height=bsz)

                    # Coluna de comandos ao lado do JOG.
                    command_x = 140
                    command_w = 202
                    command_label_w = 92
                    command_entry_w = 53
                    compact_button_h=28
                    compact_gap=2
                    self.Label_Current_Position.place(x=command_x, y=jog_top,
                                                        width=command_label_w, height=compact_button_h)
                    self.Display_CurrentX.place(x=command_x+command_label_w, y=jog_top,
                                                width=command_entry_w, height=compact_button_h)
                    self.Display_CurrentY.place(x=command_x+command_label_w+57, y=jog_top,
                                                width=command_entry_w, height=compact_button_h)

                    command_row=compact_button_h+compact_gap
                    self.GoTo_Button.place(x=command_x, y=jog_top+command_row,
                                           width=command_label_w, height=compact_button_h)
                    self.Entry_GoToX.place(x=command_x+command_label_w, y=jog_top+command_row,
                                           width=command_entry_w, height=compact_button_h)
                    self.Entry_GoToY.place(x=command_x+command_label_w+57, y=jog_top+command_row,
                                           width=command_entry_w, height=compact_button_h)
                    self.Home_Button.place(x=command_x, y=jog_top+command_row*2,
                                           width=command_w, height=compact_button_h)
                    self.UnLock_Button.place(x=command_x, y=jog_top+command_row*3,
                                             width=command_w, height=compact_button_h+2)

                    # O passo pertence ao JOG e fica imediatamente abaixo dele.
                    jog_bottom = jog_top + bsz*3
                    self.Label_Step.place(x=12, y=jog_bottom+7, width=42, height=23)
                    self.Entry_Step.place(x=54, y=jog_bottom+7, width=52, height=23)
                    self.Label_Step_u.place_forget()
                    self.separator2.place(x=8, y=jog_bottom+37, width=334, height=1)
                    self.Label_GoToX.place_forget()
                    self.Label_GoToY.place_forget()
                    ###########################################################################
                    ###########################################################################
                else:
                    ###########################################################################
                    self.Label_Position_Control.place_forget()
                    self.separator5.place_forget()
                    ##    
                    Yloc=Yloc+50
                    Yloc=Yloc+6
                    self.Home_Button.place (x=12, y=Yloc, width=100, height=23)
                    self.UnLock_Button.place(x=12+100, y=Yloc, width=100, height=23)
                    ##
                    self.separator2.place_forget()
                    self.Label_Step.place_forget()
                    self.Label_Step_u.place_forget()
                    self.Entry_Step.place_forget()
                    self.UL_Button.place_forget()
                    self.Up_Button.place_forget()
                    self.UR_Button.place_forget()
                    self.Left_Button.place_forget()
                    self.CC_Button.place_forget()
                    self.Right_Button.place_forget()
                    self.LL_Button.place_forget()
                    self.Down_Button.place_forget()
                    self.LR_Button.place_forget()
                    self.Label_GoToX.place_forget()
                    self.Label_GoToY.place_forget()
                    self.GoTo_Button.place_forget()
                    self.Entry_GoToX.place_forget()
                    self.Entry_GoToY.place_forget()
                    self.Label_Current_Position.place_forget()
                    self.Display_CurrentX.place_forget()
                    self.Display_CurrentY.place_forget()
                    ###########################################################################

                #From Bottom up
                BUinit = self.h-70
                Yloc = BUinit
                self.Preview_Button.place(x=12, y=Yloc, width=82, height=standard_button_h)
                self.Preview_Menu_Button.place(x=94, y=Yloc, width=23, height=standard_button_h)
                self.Run_Button.place   (x=121, y=Yloc, width=105, height=standard_button_h)
                self.Pause_Button.place (x=121, y=Yloc, width=105, height=standard_button_h)
                self.Stop_Button.place  (x=230, y=Yloc, width=112, height=standard_button_h)
                self._sync_run_pause_button()
                Yloc=Yloc-10+10

                # A coluna avançada precisa de mais espaço para os textos PT-BR.
                # O valor anterior (220 px) truncava rótulos como configurações
                # do rotativo e sistema de coordenadas da entrada.
                wadv       = 320
                wadv_use   = wadv-20
                Xvert_sep  = 350
                Xadvanced  = Xvert_sep+10
                w_label_adv= wadv-80 #  110 w_entry

                if self.GcodeData.ecoords == []:
                    self.Grun_Button.place_forget()
                    self.Check_Gcde.place_forget()
                    self.Gcode_Speed_Display.place_forget()
                    self.Color_Gcde.place_forget()
                    self.Reng_Veng_Vcut_Button.place_forget()
                    self.Reng_Veng_Button.place_forget()
                    self.Veng_Vcut_Button.place_forget()

                    Yloc=Yloc-30
                    self.Vcut_Button.place(x=x_process, y=Yloc, width=w_process, height=23)
                    self.Check_Vcut.place(x=x_enabled, y=Yloc, width=w_enabled, height=23)
                    self.Entry_Vcut_feed.place(x=x_speed, y=Yloc, width=w_speed, height=23)
                    self.Label_Vcut_passes.place_forget()
                    self.Entry_Vcut_passes.place(x=x_pass_entry, y=Yloc, width=w_pass, height=23)
                    speed_suffix_w=min(29, w_speed-20)
                    self.Speed_Units[2].place(x=x_speed+w_speed-speed_suffix_w-2, y=Yloc+2,
                                              width=speed_suffix_w, height=19)
                    self.Passes_Units[2].place(x=x_pass_entry+w_pass-16, y=Yloc+2,
                                               width=14, height=19)
                    self.Color_Vcut.place(x=x_color, y=Yloc+3, width=22, height=17)
                    if (self.display_power):
                        self.Label_Vcut_feed_u.place_forget()
                        self.Entry_Vcut_power.place(x=x_power_table, y=Yloc, width=w_power, height=23)
                    else:
                        self.Entry_Vcut_power.place_forget()
                        self.Label_Vcut_feed_u.place_forget()
                    Y_Vcut=Yloc

                    Yloc=Yloc-30
                    self.Veng_Button.place(x=x_process, y=Yloc, width=w_process, height=23)
                    self.Check_Veng.place(x=x_enabled, y=Yloc, width=w_enabled, height=23)
                    self.Entry_Veng_feed.place(x=x_speed, y=Yloc, width=w_speed, height=23)
                    self.Label_Veng_passes.place_forget()
                    self.Entry_Veng_passes.place(x=x_pass_entry, y=Yloc, width=w_pass, height=23)
                    self.Speed_Units[1].place(x=x_speed+w_speed-speed_suffix_w-2, y=Yloc+2,
                                              width=speed_suffix_w, height=19)
                    self.Passes_Units[1].place(x=x_pass_entry+w_pass-16, y=Yloc+2,
                                               width=14, height=19)
                    self.Color_Veng.place(x=x_color, y=Yloc+3, width=22, height=17)

                    if (self.display_power):
                        self.Label_Veng_feed_u.place_forget()
                        self.Entry_Veng_power.place(x=x_power_table, y=Yloc, width=w_power, height=23)
                    else:
                        self.Entry_Veng_power.place_forget()
                        self.Label_Veng_feed_u.place_forget()
                    Y_Veng=Yloc
                    
                    Yloc=Yloc-30
                    self.Reng_Button.place(x=x_process, y=Yloc, width=w_process, height=23)
                    self.Check_Reng.place(x=x_enabled, y=Yloc, width=w_enabled, height=23)
                    self.Entry_Reng_feed.place(x=x_speed, y=Yloc, width=w_speed, height=23)
                    self.Label_Reng_passes.place_forget()
                    self.Entry_Reng_passes.place(x=x_pass_entry, y=Yloc, width=w_pass, height=23)
                    self.Speed_Units[0].place(x=x_speed+w_speed-speed_suffix_w-2, y=Yloc+2,
                                              width=speed_suffix_w, height=19)
                    self.Passes_Units[0].place(x=x_pass_entry+w_pass-16, y=Yloc+2,
                                               width=14, height=19)
                    self.Color_Reng.place(x=x_color, y=Yloc+3, width=22, height=17)
                    self.Label_Gcde_passes.place_forget()
                    self.Entry_Gcde_passes.place_forget()
                    if (self.display_power):
                        self.Label_Reng_feed_u.place_forget()
                        self.Entry_Reng_power.place(x=x_power_table, y=Yloc, width=w_power, height=23)
                    else:
                        self.Entry_Reng_power.place_forget()
                        self.Label_Reng_feed_u.place_forget()

                    Y_Reng=Yloc
                    header_y=Y_Reng-38
                    self.Header_Process.place(x=x_process, y=header_y, width=w_process, height=30)
                    self.Header_Enabled.place(x=x_enabled, y=header_y, width=w_enabled, height=30)
                    self.Header_Speed.place(x=x_speed, y=header_y, width=w_speed, height=34)
                    if self.display_power:
                        self.Header_Power.place(x=x_power_table, y=header_y, width=w_power, height=30)
                    else:
                        self.Header_Power.place_forget()
                    self.Header_Passes.place(x=x_pass_entry, y=header_y, width=w_pass, height=30)
                    self.Header_Color.place(x=x_color-2, y=header_y, width=28, height=30)
                    line_positions = (header_y+34, Y_Reng+27, Y_Veng+27, Y_Vcut+27)
                    for line, line_y in zip(self.Table_Lines[:4], line_positions):
                        line.place(x=8, y=line_y, width=334, height=1)
                    self.Table_Lines[4].place_forget()
                    if False and (self.comb_vector.get() or self.comb_engrave.get()):
                        if self.comb_engrave.get():
                            self.Veng_Button.place_forget()                    
                            self.Reng_Button.place_forget()
                        if self.comb_vector.get():
                            self.Vcut_Button.place_forget()
                            self.Veng_Button.place_forget() 
                            
                        if self.comb_engrave.get():
                            if self.comb_vector.get():
                                self.Reng_Veng_Vcut_Button.place(x=12, y=Y_Reng, width=100, height=23*3+14)
                            else:
                                self.Reng_Veng_Button.place(x=12, y=Y_Reng, width=100, height=23*2+7)
                        elif self.comb_vector.get():
                            self.Veng_Vcut_Button.place(x=12, y=Y_Veng, width=100, height=23*2+7)

                    
                    if (self.display_power and h>=self.pi_mode_height):
                        Yloc=Yloc-35
                        self.Label_feed_u.place(x=x_entry_L, y=Yloc, width=w_entry, height=33)
                        self.Label_power_u.place(x=x_power_L, y=Yloc, width=w_entry, height=33)
                        #self.Label_feed_u.configure( bg = 'white', anchor=CENTER )
                        #self.Label_power_u.configure( bg = 'white', anchor=CENTER )
                    else:
                        self.Label_feed_u.place_forget()
                        self.Label_power_u.place_forget()
                        pass

                    if (self.display_test and h>=self.pi_mode_height):
                        Yloc=Yloc-30
                        self.Test_Button.place  (x=12, y=Yloc, width=100, height=23)
                        self.Entry_Test_power.place(  x=x_power_L, y=Yloc, width=w_entry, height=23)
                        self.Entry_Test_time.place(  x=x_entry_L, y=Yloc, width=w_entry, height=23)
                        
                        Yloc=Yloc-35
                        self.Label_time_u.place(x=x_entry_L, y=Yloc, width=w_entry, height=33)
                        self.Label_power2_u.place(x=x_power_L, y=Yloc, width=w_entry, height=33)
                        #self.Label_time_u.configure( bg = 'white', anchor=CENTER )
                        #self.Label_power2_u.configure( bg = 'white', anchor=CENTER )
                    else:
                        self.Test_Button.place_forget()
                        self.Entry_Test_time.place_forget()
                        self.Entry_Test_power.place_forget()
                        self.Label_time_u.place_forget()
                        self.Label_power2_u.place_forget()
                   
                    
                else:
                    for unit_label in self.Speed_Units + self.Passes_Units:
                        unit_label.place_forget()
                    self.Vcut_Button.place_forget()
                    self.Check_Vcut.place_forget()
                    self.Color_Vcut.place_forget()
                    self.Entry_Vcut_feed.place_forget()
                    self.Label_Vcut_feed_u.place_forget()
                    self.Entry_Vcut_power.place_forget()
                    
                    self.Veng_Button.place_forget()
                    self.Check_Veng.place_forget()
                    self.Color_Veng.place_forget()
                    self.Entry_Veng_feed.place_forget()
                    self.Label_Veng_feed_u.place_forget()
                    self.Entry_Veng_power.place_forget()
                    
                    self.Reng_Button.place_forget()
                    self.Check_Reng.place_forget()
                    self.Color_Reng.place_forget()
                    self.Entry_Reng_feed.place_forget()
                    self.Label_Reng_feed_u.place_forget()
                    self.Entry_Reng_power.place_forget()

                    self.Test_Button.place_forget()
                    self.Entry_Test_time.place_forget()
                    self.Entry_Test_power.place_forget()
                    self.Label_time_u.place_forget()
                    self.Label_power2_u.place_forget()

                    self.Reng_Veng_Vcut_Button.place_forget()
                    self.Reng_Veng_Button.place_forget()
                    self.Veng_Vcut_Button.place_forget()

                    self.Label_feed_u.place_forget()
                    self.Label_power_u.place_forget()
                    
                    Yloc=Yloc-30
                    self.Grun_Button.place(x=x_process, y=Yloc, width=w_process, height=23)
                    self.Check_Gcde.place(x=x_enabled, y=Yloc, width=w_enabled, height=23)
                    self.Gcode_Speed_Display.place(x=x_speed, y=Yloc, width=w_speed, height=23)
                    self.Label_Gcde_passes.place_forget()
                    self.Entry_Gcde_passes.place(x=x_pass_entry, y=Yloc, width=w_pass, height=23)
                    self.Color_Gcde.place(x=x_color, y=Yloc+3, width=22, height=17)
                    self.Label_Reng_passes.place_forget()
                    self.Entry_Reng_passes.place_forget()
                    self.Label_Veng_passes.place_forget()
                    self.Entry_Veng_passes.place_forget()
                    self.Label_Vcut_passes.place_forget()
                    self.Entry_Vcut_passes.place_forget()
                    if (self.display_power):
                        Yloc=Yloc-30
                        if (self.display_power):
                            self.Entry_Gcode_power.place(x=x_power_table, y=Yloc, width=w_power, height=23)
                        else:
                            self.Entry_Gcode_power.place_forget()
                        d=10
                        Yloc=Yloc-25-d
                        self.Label_power_u.place_forget()
                        #self.Label_power_u.configure( bg = 'white', anchor=CENTER )
                    else:
                        self.Label_power_u.place_forget()
                        self.Entry_Gcode_power.place_forget()
                        pass

                    header_y=Yloc-38
                    self.Header_Process.place(x=x_process, y=header_y, width=w_process, height=30)
                    self.Header_Enabled.place(x=x_enabled, y=header_y, width=w_enabled, height=30)
                    self.Header_Speed.place(x=x_speed, y=header_y, width=w_speed, height=34)
                    if self.display_power:
                        self.Header_Power.place(x=x_power_table, y=header_y, width=w_power, height=30)
                    else:
                        self.Header_Power.place_forget()
                    self.Header_Passes.place(x=x_pass_entry, y=header_y, width=w_pass, height=30)
                    self.Header_Color.place(x=x_color-2, y=header_y, width=28, height=30)
                    self.Table_Lines[0].place(x=8, y=header_y+34, width=334, height=1)
                    self.Table_Lines[1].place(x=8, y=Yloc+27, width=334, height=1)
                    for line in self.Table_Lines[2:]:
                        line.place_forget()

                # Separa visualmente os controles de posição da tabela de processos.
                self.separator3.place(x=8, y=header_y-6, width=334, height=1)
 
                if h>=self.pi_mode_height:
                    if (self.display_power):
                        Yloc=Yloc-5
                    else:
                        Yloc=Yloc-15
                    self.separator4.place(x=8, y=Yloc, width=334, height=1)
                else:
                    self.separator4.place_forget()
                    
                # End Left Column #

                # O antigo painel lateral "Avançado" foi substituído pelas
                # janelas contextuais do menu Configurações. A variável é
                # mantida apenas para ler arquivos de configuração antigos.
                if False:
                   
                    self.PreviewCanvas.configure( width = self.w-240-wadv, height = self.h-50 )
                    self.PreviewCanvas_frame.place(x=220+wadv, y=10)
                    self.separator_vert.place(x=220, y=10,width=2, height=self.h-50)

                    adv_Yloc=25-10 #15
                    self.Label_Advanced_column.place(x=Xadvanced, y=adv_Yloc, width=wadv_use, height=21)
                    adv_Yloc=adv_Yloc+25
                    self.separator_adv.place(x=Xadvanced, y=adv_Yloc,width=wadv_use, height=2)

                    if h>=self.pi_mode_height:
                        adv_Yloc=adv_Yloc+25-20 #15
                        self.Label_Halftone_adv.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Checkbutton_Halftone_adv.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=25, height=23)
                    
                        adv_Yloc=adv_Yloc+25
                        self.Label_Negate_adv.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Checkbutton_Negate_adv.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=25, height=23)

                        adv_Yloc=adv_Yloc+25
                        self.separator_adv2.place(x=Xadvanced, y=adv_Yloc,width=wadv_use, height=2)
                    
                        adv_Yloc=adv_Yloc+25-20
                        self.Label_Mirror_adv.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Checkbutton_Mirror_adv.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=25, height=23)

                        adv_Yloc=adv_Yloc+25
                        self.Label_Rotate_adv.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Checkbutton_Rotate_adv.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=25, height=23)

                        adv_Yloc=adv_Yloc+25
                        self.Label_inputCSYS_adv.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Checkbutton_inputCSYS_adv.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=25, height=23)
                    
                        adv_Yloc=adv_Yloc+25
                        self.separator_adv3.place(x=Xadvanced, y=adv_Yloc,width=wadv_use, height=2)

                        adv_Yloc=adv_Yloc+25-20
                        self.Label_Inside_First_adv.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Checkbutton_Inside_First_adv.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=25, height=23)
                    
                        adv_Yloc=adv_Yloc+25
                        self.Label_Rotary_Enable_adv.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Checkbutton_Rotary_Enable_adv.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=25, height=23)
                    else:
                        #self.Label_Advanced_column.place_forget()
                        #self.separator_adv.place_forget()
                        self.Label_Halftone_adv.place_forget()
                        self.Checkbutton_Halftone_adv.place_forget()
                        self.Label_Negate_adv.place_forget()
                        self.Checkbutton_Negate_adv.place_forget()
                        self.separator_adv2.place_forget()
                        self.Label_Mirror_adv.place_forget()
                        self.Checkbutton_Mirror_adv.place_forget()
                        self.Label_Rotate_adv.place_forget()
                        self.Checkbutton_Rotate_adv.place_forget()
                        self.Label_inputCSYS_adv.place_forget()
                        self.Checkbutton_inputCSYS_adv.place_forget()
                        self.separator_adv3.place_forget()
                        self.Label_Inside_First_adv.place_forget()
                        self.Checkbutton_Inside_First_adv.place_forget()
                        self.Label_Rotary_Enable_adv.place_forget()
                        self.Checkbutton_Rotary_Enable_adv.place_forget()

                    adv_Yloc = BUinit
                    self.Hide_Adv_Button.place (x=Xadvanced, y=adv_Yloc, width=wadv_use, height=30)

                    if self.RengData.image != None:
                        self.Label_inputCSYS_adv.configure(state="disabled")
                        self.Checkbutton_inputCSYS_adv.place_forget()              
                    else:
                        self.Label_inputCSYS_adv.configure(state="normal")
                        
                    if self.GcodeData.ecoords == []:
                        #adv_Yloc = adv_Yloc-40
                        self.Label_Vcut_passes.place(x=Xadvanced, y=Y_Vcut, width=w_label_adv, height=21)
                        self.Entry_Vcut_passes.place(x=Xadvanced+w_label_adv+2, y=Y_Vcut, width=w_entry, height=23)

                        #adv_Yloc=adv_Yloc-30
                        self.Label_Veng_passes.place(x=Xadvanced, y=Y_Veng, width=w_label_adv, height=21)
                        self.Entry_Veng_passes.place(x=Xadvanced+w_label_adv+2, y=Y_Veng, width=w_entry, height=23)

                        #adv_Yloc=adv_Yloc-30
                        self.Label_Reng_passes.place(x=Xadvanced, y=Y_Reng, width=w_label_adv, height=21)
                        self.Entry_Reng_passes.place(x=Xadvanced+w_label_adv+2, y=Y_Reng, width=w_entry, height=23)
                        self.Label_Gcde_passes.place_forget()
                        self.Entry_Gcde_passes.place_forget()
                        adv_Yloc = Y_Reng

                       ####
                        adv_Yloc=adv_Yloc-15
                        self.separator_comb.place(x=Xadvanced-1, y=adv_Yloc, width=wadv_use, height=2)

                        adv_Yloc=adv_Yloc-25
                        self.Label_Comb_Vector_adv.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Checkbutton_Comb_Vector_adv.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=25, height=23)
                        
                        adv_Yloc=adv_Yloc-25
                        self.Label_Comb_Engrave_adv.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Checkbutton_Comb_Engrave_adv.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=25, height=23)
                        ####
                        
                    else:
                        adv_Yloc=adv_Yloc-40
                        self.Label_Gcde_passes.place(x=Xadvanced, y=adv_Yloc, width=w_label_adv, height=21)
                        self.Entry_Gcde_passes.place(x=Xadvanced+w_label_adv+2, y=adv_Yloc, width=w_entry, height=23)
                        self.Label_Vcut_passes.place_forget()
                        self.Entry_Vcut_passes.place_forget()
                        self.Label_Veng_passes.place_forget()
                        self.Entry_Veng_passes.place_forget()
                        self.Label_Reng_passes.place_forget()
                        self.Entry_Reng_passes.place_forget()

                else:
                    self.PreviewCanvas_frame.place_forget()
                    self.separator_vert.place_forget()
                    self.Label_Advanced_column.place_forget()
                    self.separator_adv.place_forget() 
                    self.Label_Halftone_adv.place_forget()
                    self.Checkbutton_Halftone_adv.place_forget()
                    self.Label_Negate_adv.place_forget()
                    self.Checkbutton_Negate_adv.place_forget()
                    self.separator_adv2.place_forget()
                    self.Label_Mirror_adv.place_forget()
                    self.Checkbutton_Mirror_adv.place_forget()
                    self.Label_Rotate_adv.place_forget()
                    self.Checkbutton_Rotate_adv.place_forget()
                    self.Label_inputCSYS_adv.place_forget()
                    self.Checkbutton_inputCSYS_adv.place_forget()
                    self.separator_adv3.place_forget()
                    self.Label_Inside_First_adv.place_forget()
                    self.Checkbutton_Inside_First_adv.place_forget()

                    self.Label_Rotary_Enable_adv.place_forget()
                    self.Checkbutton_Rotary_Enable_adv.place_forget()

                    self.separator_comb.place_forget()
                    self.Label_Comb_Engrave_adv.place_forget()
                    self.Checkbutton_Comb_Engrave_adv.place_forget()
                    self.Label_Comb_Vector_adv.place_forget()
                    self.Checkbutton_Comb_Vector_adv.place_forget()


                    self.Hide_Adv_Button.place_forget()
                    
                    self.PreviewCanvas.configure( width = self.w-370, height = self.h-50 )
                    self.PreviewCanvas_frame.place(x=Xvert_sep, y=10)
                    self.separator_vert.place_forget()

                self.Set_Input_States()
                
            self.Plot_Data()
            
    def Recalculate_RQD_Click(self, event):
        self.menu_View_Refresh()

    def Set_Input_States(self):
        pass
            
    def Set_Input_States_Event(self,event):
        self.Set_Input_States()

    def Set_Input_States_RASTER(self,event=None):
        if self.halftone.get():
            self.Label_Halftone_DPI.configure(state="normal")
            self.Halftone_DPI_OptionMenu.configure(state="normal")
            self.Label_Halftone_u.configure(state="normal")
            self.Label_bezier_M1.configure(state="normal")
            self.bezier_M1_Slider.configure(state="normal")
            self.Label_bezier_M2.configure(state="normal")
            self.bezier_M2_Slider.configure(state="normal")
            self.Label_bezier_weight.configure(state="normal")
            self.bezier_weight_Slider.configure(state="normal")
        else:
            self.Label_Halftone_DPI.configure(state="disabled")
            self.Halftone_DPI_OptionMenu.configure(state="disabled")
            self.Label_Halftone_u.configure(state="disabled")
            self.Label_bezier_M1.configure(state="disabled")
            self.bezier_M1_Slider.configure(state="disabled")
            self.Label_bezier_M2.configure(state="disabled")
            self.bezier_M2_Slider.configure(state="disabled")
            self.Label_bezier_weight.configure(state="disabled")
            self.bezier_weight_Slider.configure(state="disabled")

    def Set_Input_States_BATCH(self):
        if self.post_exec.get():
            self.Entry_Batch_Path.configure(state="normal")
        else:
            self.Entry_Batch_Path.configure(state="disabled")
##    def Set_Input_States_Unsharp(self,event=None):        
##        if self.unsharp_flag.get():
##            self.Label_Unsharp_Radius.configure(state="normal")
##            self.Label_Unsharp_Radius_u.configure(state="normal")
##            self.Entry_Unsharp_Radius.configure(state="normal")
##            self.Label_Unsharp_Percent.configure(state="normal")
##            self.Label_Unsharp_Percent_u.configure(state="normal")
##            self.Entry_Unsharp_Percent.configure(state="normal")
##            self.Label_Unsharp_Threshold.configure(state="normal")
##            self.Entry_Unsharp_Threshold.configure(state="normal")
##
##        else:
##            self.Label_Unsharp_Radius.configure(state="disabled")
##            self.Label_Unsharp_Radius_u.configure(state="disabled")
##            self.Entry_Unsharp_Radius.configure(state="disabled")
##            self.Label_Unsharp_Percent.configure(state="disabled")
##            self.Label_Unsharp_Percent_u.configure(state="disabled")
##            self.Entry_Unsharp_Percent.configure(state="disabled")
##            self.Label_Unsharp_Threshold.configure(state="disabled")
##            self.Entry_Unsharp_Threshold.configure(state="disabled")

    def Set_Input_States_Rotary(self,event=None):
        if self.rotary.get():
            self.Label_Laser_R_Scale.configure(state="normal")
            self.Entry_Laser_R_Scale.configure(state="normal")
            self.Label_Laser_Rapid_Feed.configure(state="normal")
            self.Label_Laser_Rapid_Feed_u.configure(state="normal")
            self.Entry_Laser_Rapid_Feed.configure(state="normal")
        else:
            self.Label_Laser_R_Scale.configure(state="disabled")
            self.Entry_Laser_R_Scale.configure(state="disabled")
            self.Label_Laser_Rapid_Feed.configure(state="disabled")
            self.Label_Laser_Rapid_Feed_u.configure(state="disabled")
            self.Entry_Laser_Rapid_Feed.configure(state="disabled")
            
#    def Set_Input_States_RASTER_Event(self,event):
#        self.Set_Input_States_RASTER()

    def Imaging_Free(self,image_in,bg="#ffffff"):
        image_in = image_in.convert('L')
        wim,him = image_in.size
        image_out=PhotoImage(width=wim,height=him)
        pixel=image_in.load()
        if bg!=None:
            image_out.put(bg, to=(0,0,wim,him))
        for y in range(0,him):
            for x in range(0,wim):
                val=pixel[x,y]
                if val!=255:
                    image_out.put("#%02x%02x%02x" %(val,val,val),(x,y))
        return image_out

    ##########################################
    #        CANVAS PLOTTING STUFF           #
    ##########################################
    def _draw_machine_rulers(self, x_lft, y_top, x_rgt, y_bot,
                             model_x=None, model_y=None):
        """Draw rulers, machine axes, and the model-origin projections."""
        width = float(self.LaserXsize.get())
        height = float(self.LaserYsize.get())
        canvas_width = int(self.PreviewCanvas.cget("width"))
        canvas_height = int(self.PreviewCanvas.cget("height"))
        color = "#536170"
        label_color = "#34404c"

        visible_left = max(0, min(canvas_width, x_lft))
        visible_right = max(0, min(canvas_width, x_rgt))
        visible_top = max(0, min(canvas_height, y_top))
        visible_bottom = max(0, min(canvas_height, y_bot))
        if visible_right <= visible_left or visible_bottom <= visible_top:
            return

        # The scale bands live outside the cutting area so they never cover
        # imported geometry. Only the thin zero axes cross the work area.
        ruler_h = min(22, visible_top)
        ruler_w = min(38, visible_left)
        ruler_top = visible_top-ruler_h
        ruler_left = visible_left-ruler_w
        for value in ruler_values(width):
            fraction = value/width if width else 0.0
            x = x_rgt-fraction*(x_rgt-x_lft) if self.HomeUR.get() else x_lft+fraction*(x_rgt-x_lft)
            if visible_left <= x <= visible_right:
                self.PreviewCanvas.create_line(
                    x, visible_top, x, visible_top-(9 if value else ruler_h),
                    fill=color, tags="Ruler"
                )
                self.PreviewCanvas.create_text(
                    x+2, ruler_top+2, text=("%g" % value), anchor="nw",
                    fill=label_color, font=("TkDefaultFont", 7), tags="Ruler"
                )

        for value in ruler_values(height):
            fraction = value/height if height else 0.0
            y = y_top+fraction*(y_bot-y_top)
            if visible_top <= y <= visible_bottom:
                self.PreviewCanvas.create_line(
                    visible_left, y, visible_left-(9 if value else ruler_w), y,
                    fill=color, tags="Ruler"
                )
                self.PreviewCanvas.create_text(
                    visible_left-4, y-2, text=("%g" % value), anchor="se",
                    fill=label_color, font=("TkDefaultFont", 7), tags="Ruler"
                )

        x_zero = x_rgt if self.HomeUR.get() else x_lft
        self.PreviewCanvas.create_line(
            x_zero, ruler_top, x_zero, y_bot, fill="#1480a8", width=2,
            tags="Ruler"
        )
        self.PreviewCanvas.create_line(
            ruler_left, y_top, x_rgt, y_top, fill="#1480a8", width=2,
            tags="Ruler"
        )
        self.preview_machine_geometry = (x_lft, y_top, x_rgt, y_bot)
        self._draw_model_projections(
            x_lft, y_top, x_rgt, y_bot, model_x, model_y
        )

    def _draw_model_projections(self, x_lft, y_top, x_rgt, y_bot,
                                model_x, model_y):
        """Draw only the two guides tied to the movable model origin."""
        self.PreviewCanvas.delete("ModelProjection")
        if model_x is None or model_y is None:
            return
        canvas_width = int(self.PreviewCanvas.cget("width"))
        canvas_height = int(self.PreviewCanvas.cget("height"))
        visible_left = max(0, min(canvas_width, x_lft))
        visible_right = max(0, min(canvas_width, x_rgt))
        visible_top = max(0, min(canvas_height, y_top))
        visible_bottom = max(0, min(canvas_height, y_bot))
        ruler_top = visible_top-min(22, visible_top)
        ruler_left = visible_left-min(38, visible_left)
        tags = ("Ruler", "ModelProjection")
        if visible_left <= model_x <= visible_right:
            self.PreviewCanvas.create_line(
                model_x, model_y, model_x, ruler_top,
                fill="#d97706", width=2, dash=(6, 3), tags=tags
            )
        if visible_top <= model_y <= visible_bottom:
            self.PreviewCanvas.create_line(
                model_x, model_y, ruler_left, model_y,
                fill="#d97706", width=2, dash=(6, 3), tags=tags
            )
        self.PreviewCanvas.tag_raise("ModelProjection")

    def _refresh_model_projections(self):
        """Re-anchor projection endpoints after an incremental jog."""
        geometry = getattr(self, "preview_machine_geometry", None)
        if geometry is None:
            return
        x_lft, y_top, x_rgt, y_bot = geometry
        position_x = self.laserX + self.pos_offset[0]/1000.0
        position_y = self.laserY + self.pos_offset[1]/1000.0
        model_x, model_y = model_origin_canvas(
            x_lft, y_top, x_rgt, self.PlotScale, position_x, position_y,
            home_on_right=bool(self.HomeUR.get()),
        )
        self._draw_model_projections(
            x_lft, y_top, x_rgt, y_bot, model_x, model_y
        )

    def Plot_Data(self, incremental=False):
        self.preview_render_generation += 1
        render_generation = self.preview_render_generation
        self.preview_render_active = False
        self.preview_line_buffer = [] if incremental else None
        self.PreviewCanvas.delete(ALL)
        self.calc_button.place_forget()

        for seg in self.segID:
            self.PreviewCanvas.delete(seg)
        self.segID = []
        
        cszw = int(self.PreviewCanvas.cget("width"))
        cszh = int(self.PreviewCanvas.cget("height"))
        buff=10
        ruler_left_margin=42
        ruler_top_margin=26
        plot_width=max(1, cszw-ruler_left_margin)
        plot_height=max(1, cszh-ruler_top_margin)
        wc = float(cszw/2)
        hc = float(cszh/2)        
        
        maxx = float(self.LaserXsize.get()) / self.units_scale
        minx = 0.0
        maxy = 0.0
        miny = -float(self.LaserYsize.get()) / self.units_scale
        midx=(maxx+minx)/2
        midy=(maxy+miny)/2
        
                
        if self.inputCSYS.get() and self.RengData.image == None:
            xmin,xmax,ymin,ymax = 0.0,0.0,0.0,0.0
        else:
            xmin,xmax,ymin,ymax = self.Get_Design_Bounds()           
                
        if (self.HomeUR.get()):
            XlineShift = maxx - self.laserX - (xmax-xmin)
        else:
            XlineShift = self.laserX
        YlineShift = self.laserY    
        if min((xmax-xmin),(ymax-ymin)) > 0 and self.zoom2image.get():
            self.PlotScale = max((xmax-xmin)/max(1, plot_width-buff),
                                 (ymax-ymin)/max(1, plot_height-buff))
            if self.HomeUR.get():
                x_rgt = ruler_left_margin + (xmax-minx) / self.PlotScale - self.laserX / self.PlotScale + (plot_width-(xmax-xmin)/self.PlotScale)/2
                x_lft = ruler_left_margin + (xmax-maxx) / self.PlotScale - self.laserX / self.PlotScale + (plot_width-(xmax-xmin)/self.PlotScale)/2
            else:
                x_lft = ruler_left_margin + minx / self.PlotScale - self.laserX / self.PlotScale + (plot_width-(xmax-xmin)/self.PlotScale)/2
                x_rgt = ruler_left_margin + maxx / self.PlotScale - self.laserX / self.PlotScale + (plot_width-(xmax-xmin)/self.PlotScale)/2
            y_bot = ruler_top_margin-miny / self.PlotScale + self.laserY / self.PlotScale + (plot_height-(ymax-ymin)/self.PlotScale)/2
            y_top = ruler_top_margin-maxy / self.PlotScale + self.laserY / self.PlotScale + (plot_height-(ymax-ymin)/self.PlotScale)/2
            self.segID.append( self.PreviewCanvas.create_rectangle(
                            x_lft, y_bot, x_rgt, y_top, fill="gray80", outline="#7f8790", width=1) )
        else:
            self.PlotScale = max((maxx-minx)/max(1, plot_width-buff),
                                 (maxy-miny)/max(1, plot_height-buff))
            x_lft = ruler_left_margin + plot_width/2 + (minx-midx) / self.PlotScale
            x_rgt = ruler_left_margin + plot_width/2 + (maxx-midx) / self.PlotScale
            y_bot = ruler_top_margin + plot_height/2 + (maxy-midy) / self.PlotScale
            y_top = ruler_top_margin + plot_height/2 + (miny-midy) / self.PlotScale
            self.segID.append( self.PreviewCanvas.create_rectangle(
                            x_lft, y_bot, x_rgt, y_top, fill="gray80", outline="#7f8790", width=1) )

        model_position_x = self.laserX + self.pos_offset[0]/1000.0
        model_position_y = self.laserY + self.pos_offset[1]/1000.0
        model_origin_x, model_origin_y = model_origin_canvas(
            x_lft, y_top, x_rgt, self.PlotScale,
            model_position_x, model_position_y,
            home_on_right=bool(self.HomeUR.get()),
        )
        self._draw_machine_rulers(
            x_lft, y_top, x_rgt, y_bot, model_origin_x, model_origin_y
        )


        ######################################
        ###       Plot Raster Image        ###
        ######################################
        if self.RengData.image != None:
            if self.include_Reng.get():   
                try:
                    new_SCALE = (1.0/self.PlotScale)/self.input_dpi
                    if new_SCALE != self.SCALE:
                        self.SCALE = new_SCALE
                        nw=int(self.SCALE*self.wim)
                        nh=int(self.SCALE*self.him)

                        plot_im = self.RengData.image.convert("L")                        
##                        if self.unsharp_flag.get():
##                            from PIL import ImageFilter
##                            filter = ImageFilter.UnsharpMask()
##                            filter.radius    = float(self.unsharp_r.get())
##                            filter.percent   = int(float(self.unsharp_p.get()))
##                            filter.threshold = int(float(self.unsharp_t.get()))
##                            plot_im = plot_im.filter(filter)
                        
                        if self.negate.get():
                            plot_im = ImageOps.invert(plot_im)

                        if self.halftone.get() == False:
                            plot_im = plot_im.point(lambda x: 0 if x<128 else 255, '1')
                            plot_im = plot_im.convert("L")

                        if self.mirror.get():
                            plot_im = ImageOps.mirror(plot_im)

                        if self.rotate.get():
                            plot_im = plot_im.rotate(90,expand=True)
                            nh=int(self.SCALE*self.wim)
                            nw=int(self.SCALE*self.him)
                            
                        try:
                            self.UI_image = ImageTk.PhotoImage(
                                transparent_raster_preview(plot_im, (nw, nh))
                            )
                        except:
                            debug_message("Imaging_Free Used.")
                            self.UI_image = self.Imaging_Free(plot_im.resize((nw,nh), Image.LANCZOS))
                except:
                    self.SCALE = 1
                    debug_message(traceback.format_exc())
                    
                self.Plot_Raster(self.laserX+.001, self.laserY-.001, x_lft,y_top,self.PlotScale,im=self.UI_image)
        else:
            self.UI_image = None


        ######################################
        ###       Plot Reng Coords         ###
        ######################################
        if self.include_Rpth.get() and self.RengData.ecoords!=[]:
            loop_old = -1

            #####
            Xscale = 1/float(self.LaserXscale.get())
            Yscale = 1/float(self.LaserYscale.get())
            if self.rotary.get():
                Rscale = 1/float(self.LaserRscale.get())
                Yscale = Yscale*Rscale
            ######

            for line in self.RengData.ecoords:
                XY    = line
                x1    = XY[0]*Xscale
                y1    = XY[1]*Yscale-ymax
                loop  = XY[2]
                color = "black"
                # check and see if we need to move to a new discontinuous start point
                if (loop == loop_old):
                    self.Plot_Line(xold, yold, x1, y1, x_lft, y_top, XlineShift, YlineShift, self.PlotScale, color)
                loop_old = loop
                xold=x1
                yold=y1

            
        ######################################
        ###       Plot Veng Coords         ###
        ######################################
        if self.include_Veng.get():
            loop_old = -1
            

            plot_coords = self.VengData.ecoords
            if self.mirror.get() or self.rotate.get():
                plot_coords = self.mirror_rotate_vector_coords(plot_coords)

            self._plot_ecoord_paths(
                plot_coords, xmin, ymax, x_lft, y_top,
                XlineShift, YlineShift, "blue"
            )

        ######################################
        ###       Plot Vcut Coords         ###
        ######################################
        if self.include_Vcut.get():
            loop_old = -1

            plot_coords = self.VcutData.ecoords
            if self.mirror.get() or self.rotate.get():
                    plot_coords = self.mirror_rotate_vector_coords(plot_coords)
                
            self._plot_ecoord_paths(
                plot_coords, xmin, ymax, x_lft, y_top,
                XlineShift, YlineShift, "red"
            )

        ######################################
        ###       Plot Gcode Coords        ###
        ######################################
        if self.include_Gcde.get():  
            loop_old = -1
            scale=1

            plot_coords = self.GcodeData.ecoords
            if self.mirror.get() or self.rotate.get():
                    plot_coords = self.mirror_rotate_vector_coords(plot_coords)
                
            for line in plot_coords:
                XY    = line
                x1    = (XY[0]-xmin)*scale
                y1    = (XY[1]-ymax)*scale

                loop  = XY[2]
                # check and see if we need to move to a new discontinuous start point
                if (loop == loop_old):
                    self.Plot_Line(xold, yold, x1, y1, x_lft, y_top, XlineShift, YlineShift, self.PlotScale, "white")
                loop_old = loop
                xold=x1
                yold=y1


        ######################################
        ###       Plot Trace Coords        ###
        ######################################
        if self.trace_window.winfo_exists():  # or DEBUG:
            #####
            Xscale = 1/float(self.LaserXscale.get())
            Yscale = 1/float(self.LaserYscale.get())
            if self.rotary.get():
                Rscale = 1/float(self.LaserRscale.get())
                Yscale = Yscale*Rscale
            ######
            trace_coords = self.make_trace_path()
            for i in range(len(trace_coords)):
                trace_coords[i]=[trace_coords[i][0]*Xscale,trace_coords[i][1]*Yscale,trace_coords[i][2]]

            for line in trace_coords:
                XY    = line
                x1    = (XY[0]-xmin)*scale
                y1    = (XY[1]-ymax)*scale
                loop  = XY[2]
                # check and see if we need to move to a new discontinuous start point
                if (loop == loop_old):
                    green = "#%02x%02x%02x" % (0, 200, 0)
                    self.Plot_Line(xold, yold, x1, y1, x_lft, y_top, XlineShift, YlineShift,
                                   self.PlotScale, green, thick=2,tag_value=('LaserTag', 'trace'))
                loop_old = loop
                xold=x1
                yold=y1


        ######################################            
        self.refreshTime()
        dot_col = "grey50"
        xoff = self.pos_offset[0]/1000.0
        yoff = self.pos_offset[1]/1000.0

        if abs(self.pos_offset[0])+abs(self.pos_offset[1]) > 0:
            head_offset=True
        else:
            head_offset=False
        
        self.Plot_circle(self.laserX+xoff,self.laserY+yoff,x_lft,y_top,self.PlotScale,dot_col,radius=5,cross_hair=head_offset)

        # Raster images and vector paths are drawn after the machine frame;
        # keep scales and zero axes readable above all job content.
        self.PreviewCanvas.tag_raise("Ruler")

        if self.preview_line_buffer is not None:
            pending = self.preview_line_buffer
            self.preview_line_buffer = None
            self._render_preview_lines(pending, render_generation)

    def _plot_ecoord_paths(self, ecoords, xmin, ymax, xleft, ytop,
                           xshift, yshift, color, minimum_pixels=0.5):
        """Render each continuous path as one Canvas polyline.

        Points closer than a fraction of a screen pixel are omitted from the
        preview only. Path endpoints and the complete machining ECoords remain
        untouched.
        """
        def transform(x, y):
            return (
                xleft + ((x - xmin) + xshift) / self.PlotScale,
                ytop - ((y - ymax) + yshift) / self.PlotScale,
            )

        for line_args in iter_preview_polylines(
                ecoords, transform, minimum_pixels=minimum_pixels):
            line_options = {
                "fill": color, "capstyle": "round", "joinstyle": "round",
                "width": 0, "tags": "LaserTag",
            }
            if self.preview_line_buffer is not None:
                self.preview_line_buffer.append((line_args, line_options))
            else:
                self.segID.append(
                    self.PreviewCanvas.create_line(*line_args, **line_options)
                )

    def _render_preview_lines(self, pending, generation, start=0, batch_size=200):
        if generation != self.preview_render_generation:
            return

        if start == 0 and pending:
            self.preview_render_active = True
            self.import_progress.configure(
                mode="determinate", maximum=len(pending), value=0
            )
            self.import_progress.pack(anchor=SW, fill=X, side=BOTTOM, padx=2, pady=(1, 0))

        end = min(start + batch_size, len(pending))
        for line_args, line_options in pending[start:end]:
            self.segID.append(
                self.PreviewCanvas.create_line(*line_args, **line_options)
            )
        if pending:
            self.import_progress["value"] = end

        if end < len(pending):
            self.statusMessage.set(
                "Montando prévia... %d%%" % int(100.0 * end / len(pending))
            )
            self.master.after(
                1, lambda: self._render_preview_lines(pending, generation, end, batch_size)
            )
        else:
            self.preview_render_active = False
            self.import_progress.pack_forget()
            self.statusMessage.set("DXF importado; prévia pronta.")
        
    def Plot_Raster(self, XX, YY, Xleft, Ytop, PlotScale, im):
        if (self.HomeUR.get()):
            maxx = float(self.LaserXsize.get()) / self.units_scale
            xmin,xmax,ymin,ymax = self.Get_Design_Bounds()
            xplt = Xleft + ( maxx-XX-(xmax-xmin) )/PlotScale
        else:
            xplt = Xleft +  XX/PlotScale
            
        yplt = Ytop  - YY/PlotScale
        self.segID.append(
            self.PreviewCanvas.create_image(xplt, yplt, anchor=NW, image=self.UI_image,tags='LaserTag')
            )


    def offset_eccords(self,ecoords_in,offset_val):
        if not PYCLIPPER:
            return ecoords_in
        
        loop_num = ecoords_in[0][2]
        pco = pyclipper.PyclipperOffset()
        ecoords_out=[]
        pyclip_path = []
        for i in range(0,len(ecoords_in)):
            pyclip_path.append([ecoords_in[i][0]*1000,ecoords_in[i][1]*1000])

        pco.AddPath(pyclip_path, pyclipper.JT_ROUND, pyclipper.ET_CLOSEDPOLYGON)
        try:
            plot_coords = pco.Execute(offset_val*1000.0)[0]
            plot_coords.append(plot_coords[0])
        except:
            plot_coords=[]
            
        for i in range(0,len(plot_coords)):
            ecoords_out.append([plot_coords[i][0]/1000.0,plot_coords[i][1]/1000.0,loop_num])
        return ecoords_out
    
        
    def Plot_circle(self, XX, YY, Xleft, Ytop, PlotScale, col, radius=0, cross_hair=False):
        circle_tags = ('LaserTag','LaserDot')
        if (self.HomeUR.get()):
            maxx = float(self.LaserXsize.get()) / self.units_scale
            xplt = Xleft + maxx/PlotScale - XX/PlotScale
        else:
            xplt = Xleft + XX/PlotScale
        yplt = Ytop  - YY/PlotScale


        if cross_hair:
            radius=radius*2
            leg = int(radius*.707)
            self.segID.append(
                self.PreviewCanvas.create_polygon(
                                                xplt-radius,
                                                yplt,
                                                xplt-leg,
                                                yplt+leg,
                                                xplt,
                                                yplt+radius,
                                                xplt+leg,
                                                yplt+leg,
                                                xplt+radius,
                                                yplt,
                                                xplt+leg,
                                                yplt-leg,
                                                xplt,
                                                yplt-radius,
                                                xplt-leg,
                                                yplt-leg,
                                                fill=col,  outline=col, width = 1, stipple='gray12',tags=circle_tags ))
           
            self.segID.append(
                self.PreviewCanvas.create_line( xplt-radius,
                                                yplt,
                                                xplt+radius,
                                                yplt,
                                                fill=col, capstyle="round", width = 1, tags=circle_tags ))
            self.segID.append(
                self.PreviewCanvas.create_line( xplt,
                                                yplt-radius,
                                                xplt,
                                                yplt+radius,
                                                fill=col, capstyle="round", width = 1, tags=circle_tags ))
        else:
            self.segID.append(
                self.PreviewCanvas.create_oval(
                                                xplt-radius,
                                                yplt-radius,
                                                xplt+radius,
                                                yplt+radius,
                                                fill=col,  outline=col, width = 0, stipple='gray50',tags=circle_tags ))


    def Plot_Line(self, XX1, YY1, XX2, YY2, Xleft, Ytop, XlineShift, YlineShift, PlotScale, col, thick=0, tag_value='LaserTag'):
        xplt1 = Xleft + (XX1 + XlineShift )/PlotScale 
        xplt2 = Xleft + (XX2 + XlineShift )/PlotScale
        yplt1 = Ytop  - (YY1 + YlineShift )/PlotScale
        yplt2 = Ytop  - (YY2 + YlineShift )/PlotScale
        
        line_args = (xplt1, yplt1, xplt2, yplt2)
        line_options = {"fill": col, "capstyle": "round", "width": thick, "tags": tag_value}
        if self.preview_line_buffer is not None:
            self.preview_line_buffer.append((line_args, line_options))
        else:
            self.segID.append(self.PreviewCanvas.create_line(*line_args, **line_options))
        
    ################################################################################
    #                         Temporary Move Window                                #
    ################################################################################
    def move_head_window_temporary(self,new_pos_offset):
        if self.GUI_Disabled:
            return
        dx_inches = round(new_pos_offset[0]/1000.0,3)
        dy_inches = round(new_pos_offset[1]/1000.0,3)
        Xnew,Ynew = self.XY_in_bounds(dx_inches,dy_inches,no_size=True)

        pos_offset_X = round((Xnew-self.laserX)*1000.0)
        pos_offset_Y = round((Ynew-self.laserY)*1000.0)
        new_pos_offset = [pos_offset_X,pos_offset_Y]        
        
        if self.inputCSYS.get() and self.RengData.image == None:
            new_pos_offset = [0,0]
            xdist = -self.pos_offset[0]
            ydist = -self.pos_offset[1]
        else:
            xdist = -self.pos_offset[0] + new_pos_offset[0]
            ydist = -self.pos_offset[1] + new_pos_offset[1]
            
        if self.k40 != None:
            if self.Send_Rapid_Move( xdist,ydist ):
                old_pos_offset = self.pos_offset
                self.pos_offset = new_pos_offset
                self._move_preview_dot_by_offset_delta(
                    (new_pos_offset[0] - old_pos_offset[0]) / 1000.0,
                    (new_pos_offset[1] - old_pos_offset[1]) / 1000.0,
                )
        else:      
            old_pos_offset = self.pos_offset
            self.pos_offset = new_pos_offset
            self._move_preview_dot_by_offset_delta(
                (new_pos_offset[0] - old_pos_offset[0]) / 1000.0,
                (new_pos_offset[1] - old_pos_offset[1]) / 1000.0,
            )
    
    ################################################################################
    #                       Job and Design Settings Window                        #
    ################################################################################
    def MULTIPLE_COPIES_Window(self):
        if self.GUI_Disabled:
            return
        if self.job_document is None or not (
                self.job_document.vectors or self.job_document.fills or self.job_document.rasters):
            self.statusbar.configure(bg='yellow')
            self.statusMessage.set("Importe um DXF vetorial antes de criar múltiplas cópias.")
            return

        document = self.job_document
        base_objects = [*document.vectors, *document.fills, *document.rasters]
        base_bounds = Bounds.union(item.bounds for item in base_objects)
        if base_bounds is None or base_bounds.width <= 0.0 or base_bounds.height <= 0.0:
            self.statusMessage.set("O desenho atual não possui dimensões válidas para um array.")
            return

        existing = document.arrays[0] if document.arrays else None
        copies = Toplevel(self.master)
        copies.title("Múltiplas Cópias")
        copies.geometry("700x620")
        copies.minsize(700, 620)
        copies.resizable(0, 0)
        copies.transient(self.master)
        copies.grab_set()

        mode = StringVar(value=existing.mode if existing else "grid")
        columns = StringVar(value=str(existing.columns if existing else 2))
        rows = StringVar(value=str(existing.rows if existing else 2))
        spacing = StringVar(value="%.3f" % (existing.spacing_mm if existing else 2.0))
        default_stagger = (base_bounds.width + float(spacing.get())) / 2.0
        stagger_x = StringVar(value="%.3f" % (
            existing.stagger_x_mm if existing else default_stagger
        ))
        row_adjust_y = StringVar(value="%.3f" % (
            existing.row_adjust_y_mm if existing else 0.0
        ))
        summary = StringVar()
        warning = StringVar()

        container = Frame(copies, padx=12, pady=10)
        container.pack(fill=BOTH, expand=1)

        mode_frame = LabelFrame(container, text="Modo de distribuição", padx=8, pady=4)
        mode_frame.pack(fill=X, pady=(0, 5))
        Radiobutton(mode_frame, text="Grade", variable=mode, value="grid").pack(
            side=LEFT, padx=(4, 30))
        Radiobutton(mode_frame, text="Zig-zag compacto", variable=mode,
                    value="staggered").pack(side=LEFT)

        values = LabelFrame(container, text="Distribuição", padx=8, pady=5)
        values.pack(fill=X, pady=(0, 5))
        labels = (
            ("Colunas", columns), ("Linhas", rows),
            ("Espaçamento entre peças (mm)", spacing),
            ("Desvio X da linha alternada (mm)", stagger_x),
            ("Ajuste Y entre linhas (mm)", row_adjust_y),
        )
        entries = []
        for index, (text_value, variable) in enumerate(labels):
            row = index // 3
            column = (index % 3)*2
            Label(values, text=text_value, anchor=W).grid(
                row=row, column=column, sticky="w", padx=(4, 3), pady=3)
            if index < 2:
                entry = Spinbox(
                    values, textvariable=variable, from_=1, to=10000,
                    increment=1, justify=RIGHT, width=7,
                )
            else:
                entry = Entry(values, textvariable=variable, justify=RIGHT, width=10)
            entry.grid(row=row, column=column+1, sticky="e", padx=(0, 10), pady=3)
            entries.append(entry)
        for column in (0, 2, 4):
            values.columnconfigure(column, weight=1)

        preview = Canvas(container, width=650, height=345, bg="#c8c8c8",
                         highlightthickness=1, highlightbackground="#9aa0a6")
        preview.pack(fill=X, pady=(0, 7))
        Label(container, textvariable=summary, anchor=W).pack(fill=X)
        warning_label = Label(container, textvariable=warning, anchor=W, fg="#b42318")
        warning_label.pack(fill=X, pady=(2, 7))

        def values_from_ui():
            column_count = int(columns.get())
            row_count = int(rows.get())
            gap = float(spacing.get().replace(",", "."))
            stagger = float(stagger_x.get().replace(",", "."))
            adjust_y = float(row_adjust_y.get().replace(",", "."))
            if column_count < 1 or row_count < 1:
                raise ValueError("Linhas e colunas precisam ser maiores que zero.")
            if column_count*row_count > 10000:
                raise ValueError("O limite desta versão é de 10.000 cópias.")
            return InstanceArray(
                "array:main", tuple(item.id for item in base_objects),
                columns=column_count, rows=row_count, spacing_mm=gap,
                mode=mode.get(), stagger_x_mm=stagger,
                row_adjust_y_mm=adjust_y,
            )

        def refresh_preview(*unused):
            preview.delete(ALL)
            is_staggered = mode.get() == "staggered"
            entries[3].configure(state=NORMAL if is_staggered else DISABLED)
            entries[4].configure(state=NORMAL if is_staggered else DISABLED)
            try:
                array = values_from_ui()
                from k40core.arrays import instance_offsets
                offsets = list(instance_offsets(array, base_bounds))
                result_bounds = instance_array_bounds(
                    array, {item.id: item.bounds for item in base_objects}
                )
                canvas_width = int(preview.cget("width"))
                canvas_height = int(preview.cget("height"))
                machine_factor = 1.0 if self.units.get() == "mm" else 25.4
                machine_width = float(self.LaserXsize.get())*machine_factor
                machine_height = float(self.LaserYsize.get())*machine_factor
                scale = max(machine_width/max(1, canvas_width-24),
                            machine_height/max(1, canvas_height-24), 1e-9)
                area_width = machine_width/scale
                area_height = machine_height/scale
                area_left = (canvas_width-area_width)/2.0
                area_top = (canvas_height-area_height)/2.0
                preview.create_rectangle(
                    area_left, area_top, area_left+area_width, area_top+area_height,
                    fill="#ededed", outline="#59636e", width=2,
                )
                shown = offsets[:500]
                for offset_x, offset_y in shown:
                    x0 = area_left+(base_bounds.min_x+offset_x-result_bounds.min_x)/scale
                    y0 = area_top+(base_bounds.min_y+offset_y-result_bounds.min_y)/scale
                    x1 = area_left+(base_bounds.max_x+offset_x-result_bounds.min_x)/scale
                    y1 = area_top+(base_bounds.max_y+offset_y-result_bounds.min_y)/scale
                    preview.create_rectangle(x0, y0, x1, y1, outline="#b42318")
                total = array.columns*array.rows
                step_x, step_y = array_steps(array, base_bounds)
                summary.set(
                    "%d cópias | passo X %.2f mm | passo Y %.2f mm | área %.2f × %.2f mm" %
                    (total, step_x, step_y, result_bounds.width, result_bounds.height)
                )
                messages = []
                if result_bounds.width > machine_width or result_bounds.height > machine_height:
                    messages.append("O array ultrapassa a área útil configurada.")
                if total > len(shown):
                    messages.append("Prévia simplificada às primeiras 500 cópias.")
                warning.set(" ".join(messages))
                return array
            except (ValueError, TypeError) as exc:
                summary.set("")
                warning.set(str(exc))
                return None

        def fill_available():
            try:
                gap = float(spacing.get().replace(",", "."))
                stagger = float(stagger_x.get().replace(",", "."))
                adjust_y = float(row_adjust_y.get().replace(",", "."))
                machine_factor = 1.0 if self.units.get() == "mm" else 25.4
                calculated = maximum_array_counts(
                    base_bounds,
                    float(self.LaserXsize.get())*machine_factor,
                    float(self.LaserYsize.get())*machine_factor,
                    gap, mode.get(), stagger, adjust_y,
                )
                columns.set(str(calculated[0]))
                rows.set(str(calculated[1]))
                refresh_preview()
            except (ValueError, TypeError) as exc:
                warning.set(str(exc))

        def reset_stagger():
            try:
                gap = float(spacing.get().replace(",", "."))
                stagger_x.set("%.3f" % ((base_bounds.width+gap)/2.0))
                row_adjust_y.set("0.000")
            except ValueError:
                warning.set("Informe um espaçamento válido.")

        def apply():
            array = refresh_preview()
            if array is None:
                return
            previous_arrays = list(document.arrays)
            document.arrays[:] = [] if array.columns*array.rows == 1 else [array]
            document.validate()
            copies.destroy()
            self._rebuild_array_legacy_data(previous_arrays)

        def remove():
            previous_arrays = list(document.arrays)
            document.arrays.clear()
            copies.destroy()
            self._rebuild_array_legacy_data(previous_arrays)

        controls = Frame(container)
        controls.pack(fill=X, pady=(2, 0))
        Button(controls, text="Preencher área disponível", command=fill_available).pack(
            side=LEFT, padx=(0, 6))
        Button(controls, text="Restaurar encaixe padrão", command=reset_stagger).pack(
            side=LEFT)
        Button(controls, text="Aplicar", width=11, command=apply).pack(side=RIGHT)
        Button(controls, text="Cancelar", width=11, command=copies.destroy).pack(
            side=RIGHT, padx=6)
        Button(controls, text="Remover cópias", width=14, command=remove).pack(side=RIGHT)

        for variable in (mode, columns, rows, spacing, stagger_x, row_adjust_y):
            trace_variable(variable, refresh_preview)
        refresh_preview()

    def EDIT_VECTOR_Window(self):
        """Open the non-destructive editor for an imported canonical job."""
        if self.GUI_Disabled:
            return
        if self.job_document is None:
            self.statusbar.configure(bg='yellow')
            self.statusMessage.set("Importe um DXF antes de editar o desenho.")
            return
        bounds = editable_bounds(self.job_document)
        if bounds is None or bounds.width <= 0.0 or bounds.height <= 0.0:
            self.statusbar.configure(bg='yellow')
            self.statusMessage.set("O desenho não possui dimensões válidas para edição.")
            return

        editor = Toplevel(self.master)
        editor.title("Editar desenho")
        editor.geometry("500x410")
        editor.minsize(500, 410)
        editor.resizable(0, 0)
        editor.transient(self.master)
        editor.grab_set()

        scale_percent = StringVar(value="100")
        width_mm = StringVar()
        height_mm = StringVar()
        angle_degrees = StringVar(value="0")
        summary = StringVar()
        scale_preview = StringVar()
        message = StringVar()
        synchronizing = [False]
        applying = [False]
        action_buttons = []

        container = Frame(editor, padx=12, pady=10)
        container.pack(fill=BOTH, expand=1)
        Label(container, textvariable=summary, anchor=W).grid(
            row=0, column=0, sticky="ew", pady=(0, 2))
        Label(container, textvariable=scale_preview, anchor=W, fg="#2563eb").grid(
            row=1, column=0, sticky="ew", pady=(0, 8))
        container.columnconfigure(0, weight=1)

        scale_frame = LabelFrame(container, text=" Escala e dimensões ", padx=10, pady=7)
        scale_frame.grid(row=2, column=0, sticky="ew", pady=(0, 7))
        scale_frame.columnconfigure(1, weight=1)
        Label(scale_frame, image=self.ui_icons["transform"]).grid(
            row=0, column=0, rowspan=3, padx=(0, 6))
        Label(scale_frame, text="Escala").grid(row=0, column=1, sticky=W)
        Entry(scale_frame, textvariable=scale_percent, justify=RIGHT, width=10).grid(
            row=0, column=2, padx=(7, 3))
        Label(scale_frame, text="%").grid(row=0, column=3, sticky=W)
        Label(scale_frame, text="Largura").grid(row=1, column=1, sticky=W, pady=(3, 0))
        Entry(scale_frame, textvariable=width_mm, justify=RIGHT, width=10).grid(
            row=1, column=2, padx=(7, 3), pady=(3, 0))
        Label(scale_frame, text="mm").grid(row=1, column=3, sticky=W, pady=(3, 0))
        Label(scale_frame, text="Altura").grid(row=2, column=1, sticky=W, pady=(3, 0))
        Entry(scale_frame, textvariable=height_mm, justify=RIGHT, width=10).grid(
            row=2, column=2, padx=(7, 3), pady=(3, 0))
        Label(scale_frame, text="mm").grid(row=2, column=3, sticky=W, pady=(3, 0))

        rotation_frame = LabelFrame(container, text=" Rotação ", padx=10, pady=7)
        rotation_frame.grid(row=3, column=0, sticky="ew", pady=(0, 7))
        rotation_frame.columnconfigure(1, weight=1)
        Label(rotation_frame, image=self.ui_icons["reload"]).grid(row=0, column=0, padx=(0, 6))
        Label(rotation_frame, text="Ângulo").grid(row=0, column=1, sticky=W)
        Entry(rotation_frame, textvariable=angle_degrees, justify=RIGHT, width=10).grid(
            row=0, column=2, padx=(7, 3))
        Label(rotation_frame, text="graus").grid(row=0, column=3, sticky=W)

        mirror_frame = LabelFrame(container, text=" Espelhamento ", padx=10, pady=7)
        mirror_frame.grid(row=4, column=0, sticky="ew", pady=(0, 7))
        Label(mirror_frame, text="Refletir sobre o eixo:").grid(row=0, column=0, sticky=W)

        def source_center():
            current = editable_bounds(self.job_document)
            return Point((current.min_x+current.max_x)/2.0,
                         (current.min_y+current.max_y)/2.0)

        def refresh_summary():
            current = editable_bounds(self.job_document)
            suffix = " | array ativo" if self.job_document.arrays else ""
            summary.set("Peça fonte: %.2f × %.2f mm%s" % (
                current.width, current.height, suffix))

        def set_scale_values(width, height):
            synchronizing[0] = True
            width_mm.set("%.3f" % width)
            height_mm.set("%.3f" % height)
            synchronizing[0] = False

        def update_scale_preview(width, height):
            scale_preview.set("Bounding box após escala: %.3f × %.3f mm" % (width, height))

        def sync_from_percent(*unused):
            if synchronizing[0]:
                return
            try:
                current = editable_bounds(self.job_document)
                factor = float(scale_percent.get().replace(",", "."))/100.0
                if factor <= 0.0:
                    raise ValueError
                set_scale_values(current.width*factor, current.height*factor)
                update_scale_preview(current.width*factor, current.height*factor)
                message.set("")
            except ValueError:
                scale_preview.set("Informe uma escala positiva.")

        def sync_from_width(*unused):
            if synchronizing[0]:
                return
            try:
                current = editable_bounds(self.job_document)
                width = float(width_mm.get().replace(",", "."))
                if width <= 0.0:
                    raise ValueError
                factor = width/current.width
                synchronizing[0] = True
                scale_percent.set("%.6g" % (factor*100.0))
                height_mm.set("%.3f" % (current.height*factor))
                synchronizing[0] = False
                update_scale_preview(width, current.height*factor)
                message.set("")
            except ValueError:
                scale_preview.set("Informe uma largura positiva.")

        def sync_from_height(*unused):
            if synchronizing[0]:
                return
            try:
                current = editable_bounds(self.job_document)
                height = float(height_mm.get().replace(",", "."))
                if height <= 0.0:
                    raise ValueError
                factor = height/current.height
                synchronizing[0] = True
                scale_percent.set("%.6g" % (factor*100.0))
                width_mm.set("%.3f" % (current.width*factor))
                synchronizing[0] = False
                update_scale_preview(current.width*factor, height)
                message.set("")
            except ValueError:
                scale_preview.set("Informe uma altura positiva.")

        def set_actions_enabled(enabled):
            state = NORMAL if enabled else DISABLED
            for button in action_buttons:
                button.configure(state=state)

        def complete_edit(success):
            applying[0] = False
            if editor.winfo_exists():
                set_actions_enabled(True)
                if success:
                    refresh_summary()
                    synchronizing[0] = True
                    scale_percent.set("100")
                    angle_degrees.set("0")
                    synchronizing[0] = False
                    current = editable_bounds(self.job_document)
                    set_scale_values(current.width, current.height)
                    update_scale_preview(current.width, current.height)
                else:
                    message.set("Não foi possível aplicar a alteração. Veja o aviso na barra inferior.")

        def apply_scale():
            try:
                factor = float(scale_percent.get().replace(",", "."))/100.0
                if factor <= 0.0:
                    raise ValueError("A escala precisa ser um número positivo.")
                start_edit(
                    uniform_scale(factor, source_center()),
                    "Escala aplicada: %.2f%%." % (factor*100.0),
                )
            except ValueError as exc:
                message.set(str(exc))

        def apply_rotation():
            try:
                degrees = float(angle_degrees.get().replace(",", "."))
                start_edit(
                    rotation(degrees, source_center()),
                    "Rotação aplicada: %.2f°." % degrees,
                )
            except ValueError as exc:
                message.set(str(exc))

        def apply_reflection(horizontal):
            start_edit(
                reflection(horizontal, source_center()),
                "Espelhamento %s aplicado." % ("horizontal" if horizontal else "vertical"),
            )

        def start_edit(transform, success_message):
            if applying[0]:
                return
            applying[0] = True
            set_actions_enabled(False)
            started = self._apply_document_edit(transform, success_message, complete_edit)
            if not started:
                complete_edit(False)

        scale_button = Button(scale_frame, text="Aplicar", image=self.ui_icons["transform"],
                              compound=LEFT, command=apply_scale)
        scale_button.grid(row=0, column=4, rowspan=3, sticky="ns", padx=(12, 0))
        rotate_button = Button(rotation_frame, text="Aplicar", image=self.ui_icons["reload"],
                               compound=LEFT, command=apply_rotation)
        rotate_button.grid(row=0, column=4, sticky="ew", padx=(12, 0))
        mirror_x_button = Button(mirror_frame, text="Horizontal", image=self.ui_icons["mirror_horizontal"],
                                 compound=LEFT, command=lambda: apply_reflection(True))
        mirror_x_button.grid(row=0, column=1, sticky="ew", padx=(12, 5))
        mirror_y_button = Button(mirror_frame, text="Vertical", image=self.ui_icons["mirror_vertical"],
                                 compound=LEFT, command=lambda: apply_reflection(False))
        mirror_y_button.grid(row=0, column=2, sticky="ew")
        action_buttons.extend((scale_button, rotate_button, mirror_x_button, mirror_y_button))
        footer = Frame(container)
        footer.grid(row=5, column=0, sticky="ew", pady=(2, 0))
        footer.columnconfigure(0, weight=1)
        Label(footer, text="As ações são aplicadas imediatamente.", fg="#4b5563", anchor=W).grid(
            row=0, column=0, sticky="w")
        cancel_button = Button(footer, text="Cancelar", width=10, command=editor.destroy)
        cancel_button.grid(row=0, column=1, padx=(6, 4))
        ok_button = Button(footer, text="OK", width=10, command=editor.destroy)
        ok_button.grid(row=0, column=2)
        action_buttons.extend((cancel_button, ok_button))
        Label(container, textvariable=message, fg="#b42318", anchor=W).grid(
            row=6, column=0, sticky="ew")
        trace_variable(scale_percent, sync_from_percent)
        trace_variable(width_mm, sync_from_width)
        trace_variable(height_mm, sync_from_height)
        refresh_summary()
        sync_from_percent()

    def _apply_document_edit(self, transform, success_message, on_complete=None):
        """Mutate canonical transforms then rebuild legacy data off the Tk thread."""
        if self.job_document is None or self.array_build_thread is not None:
            return False
        document = self.job_document
        previous = (list(document.vectors), list(document.rasters), list(document.fills))

        def rollback():
            document.vectors[:], document.rasters[:], document.fills[:] = previous
            document.validate()

        try:
            apply_document_transform(document, transform)
        except Exception:
            rollback()
            raise
        self._rebuild_array_legacy_data(
            rollback=rollback,
            progress_message="Atualizando desenho editado...",
            success_message=success_message,
            failure_message="Falha ao editar desenho",
            on_complete=on_complete,
        )
        return True

    def _rebuild_array_legacy_data(self, previous_arrays=None, rollback=None,
                                   progress_message="Preparando múltiplas cópias...",
                                   success_message=None,
                                   failure_message="Falha ao criar múltiplas cópias",
                                   on_complete=None):
        if self.job_document is None or self.array_build_thread is not None:
            return
        self.set_gui("disabled")
        self.statusbar.configure(bg='#f0ad4e')
        self.statusMessage.set(progress_message)
        self.import_progress.configure(mode="indeterminate", maximum=100, value=0)
        self.import_progress.pack(anchor=SW, fill=X, side=BOTTOM, padx=2, pady=(1, 0))
        self.import_progress.start(12)
        self.array_build_queue = queue.Queue()
        self.array_previous_arrays = previous_arrays
        self.document_rebuild_rollback = rollback
        self.document_rebuild_success_message = success_message
        self.document_rebuild_failure_message = failure_message
        self.document_rebuild_on_complete = on_complete
        document = self.job_document

        def worker():
            try:
                cut_lines = vector_lines_in_inches(document, Operation.VECTOR_CUT)
                engrave_lines = vector_lines_in_inches(document, Operation.VECTOR_ENGRAVE)
                cut_data, engrave_data = ECoord(), ECoord()
                cut_data.make_ecoords(cut_lines, scale=1.0)
                engrave_data.make_ecoords(engrave_lines, scale=1.0)
                requested_raster_dpi = self.source_raster_dpi or self.input_dpi
                raster_dpi = requested_raster_dpi
                if document.fills:
                    raster_dpi = dpi_for_pixel_budget(
                        document.bounds, requested_raster_dpi, 50_000_000
                    )
                    raster_image = rasterize_fills(
                        document, raster_dpi, maximum_pixels=50_000_000
                    )
                else:
                    raster_image = None
                self.array_build_queue.put(
                    ("complete", (cut_data, engrave_data, raster_image, raster_dpi))
                )
            except Exception as exc:
                self.array_build_queue.put(("error", exc))

        self.array_build_thread = threading.Thread(
            target=worker, name="k40-array-build", daemon=True
        )
        self.array_build_thread.start()
        self.master.after(50, self._poll_array_build)

    def _poll_array_build(self):
        try:
            event, payload = self.array_build_queue.get_nowait()
        except queue.Empty:
            if self.array_build_thread is not None:
                self.master.after(50, self._poll_array_build)
            return

        self.import_progress.stop()
        self.import_progress.pack_forget()
        self.array_build_thread = None
        self.array_build_queue = None
        self.set_gui("normal")
        if event == "error":
            on_complete = self.document_rebuild_on_complete
            if self.document_rebuild_rollback is not None:
                self.document_rebuild_rollback()
            elif self.array_previous_arrays is not None:
                self.job_document.arrays[:] = self.array_previous_arrays
            self.array_previous_arrays = None
            self.document_rebuild_rollback = None
            self.statusbar.configure(bg='red')
            self.statusMessage.set("%s: %s" % (self.document_rebuild_failure_message, payload))
            self.document_rebuild_failure_message = None
            self.document_rebuild_success_message = None
            self.document_rebuild_on_complete = None
            if on_complete is not None:
                on_complete(False)
            return

        self.VcutData, self.VengData, raster_image, raster_dpi = payload
        previous_raster_dpi = self.input_dpi
        if raster_image is not None:
            self.RengData.set_image(raster_image)
            self.input_dpi = raster_dpi
            self.wim, self.him = raster_image.size
            self.aspect_ratio = float(self.wim-1) / float(max(1, self.him-1))
            self.SCALE = 0
        self.array_previous_arrays = None
        success_message = self.document_rebuild_success_message
        on_complete = self.document_rebuild_on_complete
        self.document_rebuild_rollback = None
        self.document_rebuild_success_message = None
        self.document_rebuild_failure_message = None
        self.document_rebuild_on_complete = None
        bounds = self.job_document.bounds
        if bounds is not None:
            self.Design_bounds = (
                bounds.min_x/25.4, bounds.max_x/25.4,
                bounds.min_y/25.4, bounds.max_y/25.4,
            )
        total = (self.job_document.arrays[0].columns*self.job_document.arrays[0].rows
                 if self.job_document.arrays else 1)
        self.statusbar.configure(bg='white')
        if success_message is not None:
            if raster_image is not None and raster_dpi < previous_raster_dpi-0.01:
                success_message += " Raster ajustado para %.0f DPI." % raster_dpi
            self.statusMessage.set(success_message)
        elif raster_image is not None and raster_dpi < previous_raster_dpi-0.01:
            self.statusMessage.set(
                "Múltiplas cópias: %d peças; raster ajustado para %.0f DPI." %
                (total, raster_dpi)
            )
        else:
            self.statusMessage.set("Múltiplas cópias aplicadas: %d peças." % total)
        self.menu_View_Refresh(incremental=True)
        if on_complete is not None:
            on_complete(True)

    def JOB_Settings_Window(self):
        if self.GUI_Disabled:
            return

        job_settings = Toplevel(self.master)
        job_settings.title("Trabalho e desenho")
        job_settings.iconname("Trabalho e desenho")
        job_settings.geometry("620x350")
        job_settings.minsize(620,350)
        job_settings.resizable(1,0)
        job_settings.transient(self.master)
        job_settings.grab_set()
        job_settings.focus_set()

        container = Frame(job_settings, padx=16, pady=14)
        container.pack(fill=BOTH, expand=1)
        container.columnconfigure(0, weight=1)

        transform_frame = LabelFrame(container, text="Transformações e posicionamento", padx=12, pady=8)
        transform_frame.grid(row=0, column=0, sticky="ew", pady=(0,10))
        transform_frame.columnconfigure(0, weight=1)
        transform_frame.columnconfigure(1, weight=1)

        Checkbutton(transform_frame, text="Espelhar desenho", variable=self.mirror, anchor=W).grid(
            row=0, column=0, sticky="w", padx=4, pady=4)
        Checkbutton(transform_frame, text="Girar desenho em 90°", variable=self.rotate, anchor=W).grid(
            row=0, column=1, sticky="w", padx=4, pady=4)
        Checkbutton(transform_frame, text="Usar coordenadas do arquivo", variable=self.inputCSYS, anchor=W).grid(
            row=1, column=0, columnspan=2, sticky="w", padx=4, pady=4)

        planning_frame = LabelFrame(container, text="Ordem e agrupamento", padx=12, pady=8)
        planning_frame.grid(row=1, column=0, sticky="ew", pady=(0,10))
        planning_frame.columnconfigure(0, weight=1)
        planning_frame.columnconfigure(1, weight=1)

        Checkbutton(planning_frame, text="Cortar áreas internas primeiro", variable=self.inside_first, anchor=W).grid(
            row=0, column=0, sticky="w", padx=4, pady=4)
        Checkbutton(planning_frame, text="Agrupar gravações", variable=self.comb_engrave, anchor=W).grid(
            row=1, column=0, sticky="w", padx=4, pady=4)
        Checkbutton(planning_frame, text="Agrupar operações vetoriais", variable=self.comb_vector, anchor=W).grid(
            row=1, column=1, sticky="w", padx=4, pady=4)

        note = Label(
            container,
            text="As alterações são aplicadas imediatamente ao trabalho atual.",
            anchor=W,
            fg="grey35",
        )
        note.grid(row=2, column=0, sticky="ew", pady=(0,10))

        close_button = Button(job_settings, text="Fechar", width=18, command=job_settings.destroy)
        close_button.pack(pady=(0,14))
        job_settings.protocol("WM_DELETE_WINDOW", job_settings.destroy)

    ################################################################################
    #                         General Settings Window                              #
    ################################################################################
    def GEN_Settings_Window(self):
        gen_width = 700
        gen_settings = Toplevel(width=gen_width, height=700) #460+75)
        gen_settings.grab_set() # Use grab_set to prevent user input in the main window
        gen_settings.focus_set()
        gen_settings.resizable(0,0)
        gen_settings.title('Configurações gerais')
        gen_settings.iconname("General Settings")

        D_Yloc  = 6
        D_dY = 26
        xd_label_L = 12

        w_label=220
        w_entry=40
        w_units=45
        xd_entry_L=xd_label_L+w_label+10
        xd_units_L=xd_entry_L+w_entry+5
        sep_border=10

        #Radio Button
        D_Yloc=D_Yloc+D_dY
        self.Label_Units = Label(gen_settings,text="Unidades")
        self.Label_Units.place(x=xd_label_L, y=D_Yloc, width=113, height=21)
        self.Radio_Units_IN = Radiobutton(gen_settings,text="polegadas", value="in",
                                         width="100", anchor=W)
        self.Radio_Units_IN.place(x=w_label+22, y=D_Yloc, width=75, height=23)
        self.Radio_Units_IN.configure(variable=self.units, command=self.Entry_units_var_Callback )
        self.Radio_Units_MM = Radiobutton(gen_settings,text="mm", value="mm",
                                         width="100", anchor=W)
        self.Radio_Units_MM.place(x=w_label+110, y=D_Yloc, width=75, height=23)
        self.Radio_Units_MM.configure(variable=self.units, command=self.Entry_units_var_Callback )

        D_Yloc=D_Yloc+D_dY
        self.Label_init_home = Label(gen_settings,text="Ir à origem ao inicializar")
        self.Label_init_home.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_init_home = Checkbutton(gen_settings,text="", anchor=W)
        self.Checkbutton_init_home.place(x=xd_entry_L, y=D_Yloc, width=75, height=23)
        self.Checkbutton_init_home.configure(variable=self.init_home)

        
        D_Yloc=D_Yloc+D_dY
        self.Label_post_home = Label(gen_settings,text="Após concluir o trabalho:")
        self.Label_post_home.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)

        Xoption_width = 140
        Xoption_col1  = xd_entry_L
        Xoption_col2  = xd_entry_L+Xoption_width
        Xoption_col3  = xd_entry_L+Xoption_width*2
        
        self.Checkbutton_post_home = Checkbutton(gen_settings,text="Liberar eixos", anchor=W)
        self.Checkbutton_post_home.place(x=Xoption_col1, y=D_Yloc, width=Xoption_width, height=23)
        self.Checkbutton_post_home.configure(variable=self.post_home)

        self.Checkbutton_post_beep = Checkbutton(gen_settings,text="Emitir som", anchor=W)
        self.Checkbutton_post_beep.place(x=Xoption_col2, y=D_Yloc, width=Xoption_width, height=23)
        self.Checkbutton_post_beep.configure(variable=self.post_beep)

        D_Yloc=D_Yloc+D_dY
        self.Checkbutton_post_disp = Checkbutton(gen_settings,text="Exibir relatório", anchor=W)
        self.Checkbutton_post_disp.place(x=Xoption_col1, y=D_Yloc, width=Xoption_width, height=23)
        self.Checkbutton_post_disp.configure(variable=self.post_disp)

        self.Checkbutton_post_exec = Checkbutton(gen_settings,text="Executar arquivo em lote:", anchor=W, command=self.Set_Input_States_BATCH)
        self.Checkbutton_post_exec.place(x=Xoption_col2, y=D_Yloc, width=Xoption_width, height=23)
        self.Checkbutton_post_exec.configure(variable=self.post_exec)


        self.Entry_Batch_Path = Entry(gen_settings)
        self.Entry_Batch_Path.place(x=Xoption_col3, y=D_Yloc, width=Xoption_width, height=23)
        self.Entry_Batch_Path.configure(textvariable=self.batch_path)
        

        D_Yloc=D_Yloc+D_dY
        self.Label_Preprocess_CRC = Label(gen_settings,text="Pré-processar dados CRC")
        self.Label_Preprocess_CRC.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_Preprocess_CRC = Checkbutton(gen_settings,text="", anchor=W)
        self.Checkbutton_Preprocess_CRC.place(x=xd_entry_L, y=D_Yloc, width=75, height=23)
        self.Checkbutton_Preprocess_CRC.configure(variable=self.pre_pr_crc)

        D_Yloc=D_Yloc+D_dY
        self.Label_Reduce_Memory = Label(gen_settings,text="Reduzir uso de memória")
        self.Label_Reduce_Memory.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_Reduce_Memory = Checkbutton(gen_settings,text="(necessário para desenhos grandes ou computadores com pouca memória)", anchor=W)
        self.Checkbutton_Reduce_Memory.place(x=xd_entry_L, y=D_Yloc, width=350, height=23)
        self.Checkbutton_Reduce_Memory.configure(variable=self.reduced_mem)
        trace_variable(self.reduced_mem, self.Reduced_Memory_Callback)

        D_Yloc=D_Yloc+D_dY
        self.Label_Wait = Label(gen_settings,text="Aguardar a laser concluir")
        self.Label_Wait.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_Wait = Checkbutton(gen_settings,text="(após todos os dados serem enviados por USB)", anchor=W)
        self.Checkbutton_Wait.place(x=xd_entry_L, y=D_Yloc, width=350, height=23)
        self.Checkbutton_Wait.configure(variable=self.wait)
        #trace_variable(self.wait, self.Wait_Callback)
        
        #D_Yloc=D_Yloc+D_dY
        #self.Label_Timeout = Label(gen_settings,text="USB Timeout")
        #self.Label_Timeout.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        #self.Label_Timeout_u = Label(gen_settings,text="ms", anchor=W)
        #self.Label_Timeout_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        #self.Entry_Timeout = Entry(gen_settings,width="15")
        #self.Entry_Timeout.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        #self.Entry_Timeout.configure(textvariable=self.t_timeout)
        #trace_variable(self.t_timeout, self.Entry_Timeout_Callback)
        #self.entry_set(self.Entry_Timeout,self.Entry_Timeout_Check(),2)

        #D_Yloc=D_Yloc+D_dY
        #self.Label_N_Timeouts = Label(gen_settings,text="Number of Timeouts")
        #self.Label_N_Timeouts.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        #self.Entry_N_Timeouts = Entry(gen_settings,width="15")
        #self.Entry_N_Timeouts.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        #self.Entry_N_Timeouts.configure(textvariable=self.n_timeouts)
        #trace_variable(self.n_timeouts, self.Entry_N_Timeouts_Callback)
        #self.entry_set(self.Entry_N_Timeouts,self.Entry_N_Timeouts_Check(),2)

        D_Yloc=D_Yloc+D_dY*1.25
        self.gen_separator1 = Frame(gen_settings, height=2, bd=1, relief=SUNKEN)
        self.gen_separator1.place(x=xd_label_L, y=D_Yloc,width=gen_width-40, height=2)

        D_Yloc=D_Yloc+D_dY*.25
        self.Label_Inkscape_title = Label(gen_settings,text="Opções do Inkscape")
        self.Label_Inkscape_title.place(x=xd_label_L, y=D_Yloc, width=gen_width-40, height=21)
        
        D_Yloc=D_Yloc+D_dY
        font_entry_width=215
        self.Label_Inkscape_Path = Label(gen_settings,text="Executável do Inkscape")
        self.Label_Inkscape_Path.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Entry_Inkscape_Path = Entry(gen_settings,width="15")
        self.Entry_Inkscape_Path.place(x=xd_entry_L, y=D_Yloc, width=font_entry_width, height=23)
        self.Entry_Inkscape_Path.configure(textvariable=self.inkscape_path)
        self.Entry_Inkscape_Path.bind('<FocusIn>', self.Inkscape_Path_Message)
        self.Inkscape_Path = Button(gen_settings,text="Localizar Inkscape")
        self.Inkscape_Path.place(x=xd_entry_L+font_entry_width+10, y=D_Yloc, width=110, height=23)
        self.Inkscape_Path.bind("<ButtonRelease-1>", self.Inkscape_Path_Click)

        D_Yloc=D_Yloc+D_dY
        self.Label_Ink_Timeout = Label(gen_settings,text="Tempo limite do Inkscape")
        self.Label_Ink_Timeout.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Label_Ink_Timeout_u = Label(gen_settings,text="minutos", anchor=W)
        self.Label_Ink_Timeout_u.place(x=xd_units_L, y=D_Yloc, width=w_units*2, height=21)
        self.Entry_Ink_Timeout = Entry(gen_settings,width="15")
        self.Entry_Ink_Timeout.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Ink_Timeout.configure(textvariable=self.ink_timeout)
        trace_variable(self.ink_timeout, self.Entry_Ink_Timeout_Callback)
        self.entry_set(self.Entry_Ink_Timeout,self.Entry_Ink_Timeout_Check(),2)

        D_Yloc=D_Yloc+D_dY*1.25
        self.gen_separator2 = Frame(gen_settings, height=2, bd=1, relief=SUNKEN)
        self.gen_separator2.place(x=xd_label_L, y=D_Yloc,width=gen_width-40, height=2)

        D_Yloc=D_Yloc+D_dY*.25
        self.Label_Inkscape_title2 = Label(gen_settings,text="Opções da Laser-M3")
        self.Label_Inkscape_title2.place(x=xd_label_L, y=D_Yloc, width=gen_width-40, height=21)
        
        D_Yloc=D_Yloc+D_dY
        self.Labelshow_power = Label(gen_settings,text="Mostrar configurações de potência")
        self.Labelshow_power.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbuttonshow_power = Checkbutton(gen_settings,text="", anchor=W)
        self.Checkbuttonshow_power.place(x=xd_entry_L, y=D_Yloc, width=75, height=23)
        self.Checkbuttonshow_power.configure(variable=self.show_power)
        trace_variable(self.show_power, self.menu_View_Refresh_Callback)

        D_Yloc=D_Yloc+D_dY
        self.Labelshow_test = Label(gen_settings,text="Mostrar botão de teste de disparo")
        self.Labelshow_test.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbuttonshow_test = Checkbutton(gen_settings,text="", anchor=W)
        self.Checkbuttonshow_test.place(x=xd_entry_L, y=D_Yloc, width=75, height=23)
        self.Checkbuttonshow_test.configure(variable=self.show_test)
        trace_variable(self.show_test, self.menu_View_Refresh_Callback)
        
        D_Yloc=D_Yloc+D_dY
        self.Label_Max_Power = Label(gen_settings,text="Potência máxima")
        self.Label_Max_Power.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Label_Max_Power_u = Label(gen_settings,text="%   (um valor muito alto pode danificar o tubo laser)", anchor=W)
        #self.Label_Max_Power_u.configure( bg = 'white' )

        self.Label_Max_Power_u.place(x=xd_units_L, y=D_Yloc, width=325, height=21)
        self.Entry_Max_Power = Entry(gen_settings,width="15")
        self.Entry_Max_Power.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Max_Power.configure(textvariable=self.max_power,justify='center')
        trace_variable(self.max_power, self.Entry_Max_Power_Callback)
        self.entry_set(self.Entry_Max_Power,self.Entry_Max_Power_Check(),2)

        def update_gen_settings(input1=None,input2=None,input3=None):
            self.menu_View_Refresh_Callback()
            if self.board_name.get() == "LASER-M3":
                self.Labelshow_power.configure(state="normal")
                self.Checkbuttonshow_power.configure(state="normal")
                self.Labelshow_test.configure(state="normal")
                self.Checkbuttonshow_test.configure(state="normal")
                self.Label_Max_Power.configure(state="normal")
                self.Label_Max_Power_u.configure(state="normal")
                self.Entry_Max_Power.configure(state="normal")
            else:
                self.Labelshow_power.configure(state="disabled")
                self.Checkbuttonshow_power.configure(state="disabled")
                self.Labelshow_test.configure(state="disabled")
                self.Checkbuttonshow_test.configure(state="disabled")
                self.Label_Max_Power.configure(state="disabled")
                self.Label_Max_Power_u.configure(state="disabled")
                self.Entry_Max_Power.configure(state="disabled")
                
                

        update_gen_settings()
        
        D_Yloc=D_Yloc+D_dY*1.25
        self.gen_separator3 = Frame(gen_settings, height=2, bd=1, relief=SUNKEN)
        self.gen_separator3.place(x=xd_label_L, y=D_Yloc,width=gen_width-40, height=2)
        
        D_Yloc=D_Yloc+D_dY*.5
        self.Label_no_com = Label(gen_settings,text="Origem no canto superior direito")
        self.Label_no_com.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_no_com = Checkbutton(gen_settings,text="", anchor=W)
        self.Checkbutton_no_com.place(x=xd_entry_L, y=D_Yloc, width=75, height=23)
        self.Checkbutton_no_com.configure(variable=self.HomeUR)
        trace_variable(self.HomeUR, self.menu_View_Refresh_Callback)

        D_Yloc=D_Yloc+D_dY 
        self.Label_Board_Name      = Label(gen_settings,text="Modelo da placa", anchor=CENTER )
        self.Board_Name_OptionMenu = OptionMenu(gen_settings, self.board_name,
                                            "LASER-M3",
                                            "LASER-M2",
                                            "LASER-M1",
                                            "LASER-M",
                                            "LASER-B2",
                                            "LASER-B1",
                                            "LASER-B",
                                            "LASER-A")
        trace_variable(self.board_name, update_gen_settings)
        
        self.Label_Board_Name.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Board_Name_OptionMenu.place(x=xd_entry_L, y=D_Yloc, width=w_entry*3, height=23)

        D_Yloc=D_Yloc+D_dY
        self.Label_Laser_Area_Width = Label(gen_settings,text="Largura da área da laser")
        self.Label_Laser_Area_Width.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Label_Laser_Area_Width_u = Label(gen_settings,textvariable=self.units, anchor=W)
        self.Label_Laser_Area_Width_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.Entry_Laser_Area_Width = Entry(gen_settings,width="15")
        self.Entry_Laser_Area_Width.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Laser_Area_Width.configure(textvariable=self.LaserXsize)
        trace_variable(self.LaserXsize, self.Entry_Laser_Area_Width_Callback)
        self.entry_set(self.Entry_Laser_Area_Width,self.Entry_Laser_Area_Width_Check(),2)

        D_Yloc=D_Yloc+D_dY
        self.Label_Laser_Area_Height = Label(gen_settings,text="Altura da área da laser")
        self.Label_Laser_Area_Height.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Label_Laser_Area_Height_u = Label(gen_settings,textvariable=self.units, anchor=W)
        self.Label_Laser_Area_Height_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.Entry_Laser_Area_Height = Entry(gen_settings,width="15")
        self.Entry_Laser_Area_Height.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Laser_Area_Height.configure(textvariable=self.LaserYsize)
        trace_variable(self.LaserYsize, self.Entry_Laser_Area_Height_Callback)
        self.entry_set(self.Entry_Laser_Area_Height,self.Entry_Laser_Area_Height_Check(),2)

        D_Yloc=D_Yloc+D_dY
        self.Label_Laser_X_Scale = Label(gen_settings,text="Fator de escala X")
        self.Label_Laser_X_Scale.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Entry_Laser_X_Scale = Entry(gen_settings,width="15")
        self.Entry_Laser_X_Scale.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Laser_X_Scale.configure(textvariable=self.LaserXscale)
        trace_variable(self.LaserXscale, self.Entry_Laser_X_Scale_Callback)
        self.entry_set(self.Entry_Laser_X_Scale,self.Entry_Laser_X_Scale_Check(),2)

        D_Yloc=D_Yloc+D_dY
        self.Label_Laser_Y_Scale = Label(gen_settings,text="Fator de escala Y")
        self.Label_Laser_Y_Scale.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Entry_Laser_Y_Scale = Entry(gen_settings,width="15")
        self.Entry_Laser_Y_Scale.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Laser_Y_Scale.configure(textvariable=self.LaserYscale)
        trace_variable(self.LaserYscale, self.Entry_Laser_Y_Scale_Callback)
        self.entry_set(self.Entry_Laser_Y_Scale,self.Entry_Laser_Y_Scale_Check(),2)
                
        D_Yloc=D_Yloc+D_dY+10
        self.Label_SaveConfig = Label(gen_settings,text="Arquivo de configuração")
        self.Label_SaveConfig.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)

        self.GEN_SaveConfig = Button(gen_settings,text="Salvar")
        self.GEN_SaveConfig.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=21, anchor="nw")
        self.GEN_SaveConfig.bind("<ButtonRelease-1>", self.Write_Config_File)
        
        ## Buttons ##
        gen_settings.update_idletasks()
        Ybut=int(gen_settings.winfo_height())-30
        Xbut=int(gen_settings.winfo_width()/2)

        self.GEN_Close = Button(gen_settings,text="Fechar")
        self.GEN_Close.place(x=Xbut, y=Ybut, width=130, height=30, anchor="center")
        self.GEN_Close.bind("<ButtonRelease-1>", self.Close_Current_Window_Click)

        self.Set_Input_States_BATCH()

    ################################################################################
    #                          Raster Settings Window                              #
    ################################################################################
    def RASTER_Settings_Window(self):
        Wset=425+280
        Hset=330 #260
        raster_settings = Toplevel(width=Wset, height=Hset)
        raster_settings.grab_set() # Use grab_set to prevent user input in the main window
        raster_settings.focus_set()
        raster_settings.resizable(0,0)
        raster_settings.title('Configurações de raster')
        raster_settings.iconname("Raster Settings")

        D_Yloc  = 6
        D_dY = 24
        xd_label_L = 12

        w_label=155
        w_entry=60
        w_units=35
        xd_entry_L=xd_label_L+w_label+10
        xd_units_L=xd_entry_L+w_entry+5

        D_Yloc=D_Yloc+D_dY
        self.Label_Rstep   = Label(raster_settings,text="Passo da linha de varredura", anchor=CENTER )
        self.Label_Rstep.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Label_Rstep_u = Label(raster_settings,text="in", anchor=W)
        self.Label_Rstep_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.Entry_Rstep   = Entry(raster_settings,width="15")
        self.Entry_Rstep.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Rstep.configure(textvariable=self.rast_step)
        trace_variable(self.rast_step, self.Entry_Rstep_Callback)

        D_Yloc=D_Yloc+D_dY
        self.Label_EngraveUP = Label(raster_settings,text="Gravar de baixo para cima")
        self.Checkbutton_EngraveUP = Checkbutton(raster_settings,text=" ", anchor=W)
        self.Checkbutton_EngraveUP.configure(variable=self.engraveUP)
        self.Label_EngraveUP.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_EngraveUP.place(x=w_label+22, y=D_Yloc, width=75, height=23)
        
        D_Yloc=D_Yloc+D_dY
        self.Label_Halftone = Label(raster_settings,text="Meio-tom (dithering)")
        self.Label_Halftone.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_Halftone = Checkbutton(raster_settings,text=" ", anchor=W, command=self.Set_Input_States_RASTER)
        self.Checkbutton_Halftone.place(x=w_label+22, y=D_Yloc, width=75, height=23)
        self.Checkbutton_Halftone.configure(variable=self.halftone)
        trace_variable(self.halftone, self.menu_View_Refresh_Callback)

        D_Yloc=D_Yloc+D_dY
        self.Label_Negate = Label(raster_settings,text="Inverter cores do raster")
        self.Label_Negate.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_Negate = Checkbutton(raster_settings,text=" ", anchor=W)
        self.Checkbutton_Negate.place(x=w_label+22, y=D_Yloc, width=75, height=23)
        self.Checkbutton_Negate.configure(variable=self.negate)

        ############
        D_Yloc=D_Yloc+D_dY 
        self.Label_Halftone_DPI      = Label(raster_settings,text="Resolução do meio-tom", anchor=CENTER )

        if self.reduced_mem.get():
            if self.ht_size == "1000": self.ht_size = "500"
            if self.ht_size == "333":  self.ht_size = "500"
            if self.ht_size == "200":  self.ht_size = "250"
            if self.ht_size == "143":  self.ht_size = "167"
            self.Halftone_DPI_OptionMenu = OptionMenu(raster_settings, self.ht_size,
                                                "500",
                                                "250",
                                                "167",
                                                "125")
        else:
            self.Halftone_DPI_OptionMenu = OptionMenu(raster_settings, self.ht_size,
                                                "1000",
                                                "500",
                                                "333",
                                                "250",
                                                "200",
                                                "167",
                                                "143",
                                                "125")

        self.Label_Halftone_DPI.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Halftone_DPI_OptionMenu.place(x=xd_entry_L, y=D_Yloc, width=w_entry+30, height=23)

        self.Label_Halftone_u = Label(raster_settings,text="dpi", anchor=W)
        self.Label_Halftone_u.place(x=xd_units_L+30, y=D_Yloc, width=w_units, height=21)

        ############
        D_Yloc=D_Yloc+D_dY+5
        self.Label_bezier_M1  = Label(raster_settings,
                                text="Inclinação, preto (%.1f)"%(self.bezier_M1_default),
                                anchor=CENTER )
        self.bezier_M1_Slider = Scale(raster_settings, from_=1, to=50, resolution=0.1, \
                                orient=HORIZONTAL, variable=self.bezier_M1)
        self.bezier_M1_Slider.place(x=xd_entry_L, y=D_Yloc, width=(Wset-xd_entry_L-25-280 ))
        D_Yloc=D_Yloc+21
        self.Label_bezier_M1.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        trace_variable(self.bezier_M1, self.bezier_M1_Callback)
        
        D_Yloc=D_Yloc+D_dY-8
        self.Label_bezier_M2  = Label(raster_settings,
                                text="Inclinação, branco (%.2f)"%(self.bezier_M2_default),
                                anchor=CENTER )
        self.bezier_M2_Slider = Scale(raster_settings, from_=0.0, to=1, \
                                orient=HORIZONTAL,resolution=0.01, variable=self.bezier_M2)
        self.bezier_M2_Slider.place(x=xd_entry_L, y=D_Yloc, width=(Wset-xd_entry_L-25-280 ))
        D_Yloc=D_Yloc+21
        self.Label_bezier_M2.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        trace_variable(self.bezier_M2, self.bezier_M2_Callback)

        D_Yloc=D_Yloc+D_dY-8
        self.Label_bezier_weight   = Label(raster_settings,
                                     text="Transição (%.1f)"%(self.bezier_M1_default),
                                     anchor=CENTER )
        self.bezier_weight_Slider = Scale(raster_settings, from_=0, to=10, resolution=0.1, \
                                    orient=HORIZONTAL, variable=self.bezier_weight)
        self.bezier_weight_Slider.place(x=xd_entry_L, y=D_Yloc, width=(Wset-xd_entry_L-25-280 ))
        D_Yloc=D_Yloc+21
        self.Label_bezier_weight.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        trace_variable(self.bezier_weight, self.bezier_weight_Callback)

##        show_unsharp = False
##        if DEBUG and show_unsharp:
##            D_Yloc=D_Yloc+D_dY
##            self.Label_UnsharpMask = Label(raster_settings,text="Unsharp Mask")
##            self.Label_UnsharpMask.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
##            self.Checkbutton_UnsharpMask = Checkbutton(raster_settings,text=" ", anchor=W, command=self.Set_Input_States_Unsharp)
##            self.Checkbutton_UnsharpMask.place(x=w_label+22, y=D_Yloc, width=75, height=23)
##            self.Checkbutton_UnsharpMask.configure(variable=self.unsharp_flag)
##            trace_variable(self.unsharp_flag, self.menu_View_Refresh_Callback)
##
##            D_Yloc=D_Yloc+D_dY
##            self.Label_Unsharp_Radius   = Label(raster_settings,text="Unsharp Mask Radius", anchor=CENTER )
##            self.Label_Unsharp_Radius.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
##            self.Label_Unsharp_Radius_u = Label(raster_settings,text="Pixels", anchor=W)
##            self.Label_Unsharp_Radius_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
##            self.Entry_Unsharp_Radius   = Entry(raster_settings,width="15")
##            self.Entry_Unsharp_Radius.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
##            self.Entry_Unsharp_Radius.configure(textvariable=self.unsharp_r)
##            trace_variable(self.unsharp_r, self.Entry_Unsharp_Radius_Callback)
##
##            D_Yloc=D_Yloc+D_dY
##            self.Label_Unsharp_Percent   = Label(raster_settings,text="Unsharp Mask Percent", anchor=CENTER )
##            self.Label_Unsharp_Percent.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
##            self.Label_Unsharp_Percent_u = Label(raster_settings,text="%", anchor=W)
##            self.Label_Unsharp_Percent_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
##            self.Entry_Unsharp_Percent   = Entry(raster_settings,width="15")
##            self.Entry_Unsharp_Percent.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
##            self.Entry_Unsharp_Percent.configure(textvariable=self.unsharp_p)
##            trace_variable(self.unsharp_p, self.Entry_Unsharp_Percent_Callback)
##
##            D_Yloc=D_Yloc+D_dY
##            self.Label_Unsharp_Threshold   = Label(raster_settings,text="Unsharp Mask Threshold", anchor=CENTER )
##            self.Label_Unsharp_Threshold.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
##            #self.Label_Unsharp_Threshold_u = Label(raster_settings,text="Pixels", anchor=W)
##            #self.Label_Unsharp_Threshold_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
##            self.Entry_Unsharp_Threshold   = Entry(raster_settings,width="15")
##            self.Entry_Unsharp_Threshold.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
##            self.Entry_Unsharp_Threshold.configure(textvariable=self.unsharp_t)
##            trace_variable(self.unsharp_t, self.Entry_Unsharp_Threshold_Callback)        

        # Bezier Canvas
        self.Bezier_frame = Frame(raster_settings, bd=1, relief=SUNKEN)
        self.Bezier_frame.place(x=Wset-280, y=10, height=265, width=265)
        self.BezierCanvas = Canvas(self.Bezier_frame, background="white")
        self.BezierCanvas.pack(side=LEFT, fill=BOTH, expand=1)
        self.BezierCanvas.create_line( 5,260-0,260,260-255,fill="grey75", capstyle="round", width = 2, tags='perm')


        M1 = self.bezier_M1_default
        M2 = self.bezier_M2_default
        w  = self.bezier_weight_default
        num = 10
        x,y = self.generate_bezier(M1,M2,w,n=num)
        for i in range(0,num):
            self.BezierCanvas.create_line( 5+x[i],260-y[i],5+x[i+1],260-y[i+1],fill="grey85", stipple='gray25',\
                                           capstyle="round", width = 2, tags='perm')
        

        ## Buttons ##
        raster_settings.update_idletasks()
        Ybut=int(raster_settings.winfo_height())-30
        Xbut=int(raster_settings.winfo_width()/2)

        self.RASTER_Close = Button(raster_settings,text="Fechar")
        self.RASTER_Close.place(x=Xbut, y=Ybut, width=130, height=30, anchor="center")
        self.RASTER_Close.bind("<ButtonRelease-1>", self.Close_Current_Window_Click)

        self.bezier_M1_Callback()
        self.Set_Input_States_RASTER()
        #if DEBUG and show_unsharp:
        #    self.Set_Input_States_Unsharp()


    ################################################################################
    #                         Rotary Settings Window                               #
    ################################################################################
    def ROTARY_Settings_Window(self):
        rotary_settings = Toplevel(width=520, height=175)
        rotary_settings.grab_set() # Use grab_set to prevent user input in the main window
        rotary_settings.focus_set()
        rotary_settings.resizable(0,0)
        rotary_settings.title('Configurações do rotativo')
        rotary_settings.iconname("Rotary Settings")

        D_Yloc  = 6
        D_dY = 30
        xd_label_L = 12

        w_label=300
        w_entry=40
        w_units=45
        xd_entry_L=xd_label_L+w_label+10
        xd_units_L=xd_entry_L+w_entry+5
        sep_border=10
        

        D_Yloc=D_Yloc+D_dY-15
        self.Label_Rotary_Enable = Label(rotary_settings,text="Usar configurações do rotativo")
        self.Label_Rotary_Enable.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_Rotary_Enable = Checkbutton(rotary_settings,text="", anchor=W, command=self.Set_Input_States_Rotary)
        self.Checkbutton_Rotary_Enable.place(x=xd_entry_L, y=D_Yloc, width=75, height=23)
        self.Checkbutton_Rotary_Enable.configure(variable=self.rotary)

        D_Yloc=D_Yloc+D_dY
        self.Label_Laser_R_Scale = Label(rotary_settings,text="Fator de escala do rotativo (eixo Y)")
        self.Label_Laser_R_Scale.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Entry_Laser_R_Scale = Entry(rotary_settings,width="15")
        self.Entry_Laser_R_Scale.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Laser_R_Scale.configure(textvariable=self.LaserRscale)
        trace_variable(self.LaserRscale, self.Entry_Laser_R_Scale_Callback)
        self.entry_set(self.Entry_Laser_R_Scale,self.Entry_Laser_R_Scale_Check(),2)

        D_Yloc=D_Yloc+D_dY
        self.Label_Laser_Rapid_Feed = Label(rotary_settings,text="Velocidade rápida (padrão=0)")
        self.Label_Laser_Rapid_Feed.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Label_Laser_Rapid_Feed_u = Label(rotary_settings,textvariable=self.funits, anchor=W)
        self.Label_Laser_Rapid_Feed_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.Entry_Laser_Rapid_Feed = Entry(rotary_settings,width="15")
        self.Entry_Laser_Rapid_Feed.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_Laser_Rapid_Feed.configure(textvariable=self.rapid_feed)
        trace_variable(self.rapid_feed, self.Entry_Laser_Rapid_Feed_Callback)
        self.entry_set(self.Entry_Laser_Rapid_Feed,self.Entry_Laser_Rapid_Feed_Check(),2)
        
        ## Buttons ##
        rotary_settings.update_idletasks()
        Ybut=int(rotary_settings.winfo_height())-30
        Xbut=int(rotary_settings.winfo_width()/2)

        self.GEN_Close = Button(rotary_settings,text="Fechar")
        self.GEN_Close.place(x=Xbut, y=Ybut, width=130, height=30, anchor="center")
        self.GEN_Close.bind("<ButtonRelease-1>", self.Close_Current_Window_Click)

        self.Set_Input_States_Rotary()

    ################################################################################
    #                            Trace Send Window                                 #
    ################################################################################

    def TRACE_Settings_Window(self, dummy=None):
        if self.GUI_Disabled:
            return
        trace_window = Toplevel(width=520, height=210)
        self.trace_window=trace_window
        trace_window.grab_set() # Use grab_set to prevent user input in the main window during calculations
        trace_window.resizable(0,0)
        trace_window.title('Contornar limite')
        trace_window.iconname("Trace Boundary")

        def Close_Click():
            win_id=self.grab_current()
            self.PreviewCanvas.delete('trace')
            win_id.destroy()

        def Close_and_Send_Click():
            win_id=self.grab_current()
            self.PreviewCanvas.delete('trace')
            win_id.destroy()
            self.Trace_Eng()

        self.Label_Trace_Power = Label(trace_window,text="Potência do laser durante o contorno")
        self.Entry_Trace_Power = Entry(trace_window,width="15")
        self.Label_Trace_Power_u = Label(trace_window,text="(0-10.0)", anchor=W)
        
        def Set_Input_States_Trace():
            if self.trace_w_laser.get():
                self.Label_Trace_Power.configure(state="normal")
                self.Entry_Trace_Power.configure(state="normal")
                self.Label_Trace_Power_u.configure(state="normal")
            else:
                self.Label_Trace_Power.configure(state="disabled")
                self.Entry_Trace_Power.configure(state="disabled")
                self.Label_Trace_Power_u.configure(state="disabled")

        D_Yloc  = 0
        D_dY = 28
        xd_label_L = 12

        w_label=320
        w_entry=40
        w_units=50
        xd_entry_L=xd_label_L+w_label+10
        xd_units_L=xd_entry_L+w_entry+5

        D_Yloc=D_Yloc+D_dY
        self.Label_Trace_Gap = Label(trace_window,text="Distância entre o desenho e o contorno")
        self.Label_Trace_Gap.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Entry_Trace_Gap = Entry(trace_window,width="15")
        self.Entry_Trace_Gap.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Label_Trace_Gap_u = Label(trace_window,textvariable=self.units, anchor=W)
        self.Label_Trace_Gap_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        self.Entry_Trace_Gap.configure(textvariable=self.trace_gap,justify='center')
        trace_variable(self.trace_gap, self.Entry_Trace_Gap_Callback)
        self.entry_set(self.Entry_Trace_Gap,self.Entry_Trace_Gap_Check(),2)
        if not PYCLIPPER:
            self.Label_Trace_Gap.configure(state="disabled")
            self.Label_Trace_Gap_u.configure(state="disabled")
            self.Entry_Trace_Gap.configure(state="disabled")

        D_Yloc=D_Yloc+D_dY
        self.Label_Laser_Trace = Label(trace_window,text="Laser ligado durante o contorno")
        self.Label_Laser_Trace.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_Laser_Trace = Checkbutton(trace_window,text="", anchor=W,  command=Set_Input_States_Trace)
        self.Checkbutton_Laser_Trace.place(x=xd_entry_L, y=D_Yloc, width=75, height=23)
        self.Checkbutton_Laser_Trace.configure(variable=self.trace_w_laser)
        Set_Input_States_Trace()

        green = "#%02x%02x%02x" % (0, 200, 0)
        if self.display_power:
            D_Yloc=D_Yloc+D_dY
            self.Label_Trace_Power.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
            self.Entry_Trace_Power.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
            self.Label_Trace_Power_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
            self.Entry_Trace_Power.configure(textvariable=self.Trace_power,justify='center',fg=green)
            trace_variable(self.Trace_power, self.Entry_Trace_Power_Callback)
            self.entry_set(self.Entry_Trace_Power,self.Entry_Trace_Power_Check(),2)
            if not self.trace_w_laser.get():
                self.Label_Trace_Power.configure(state="disabled")
                self.Label_Trace_Power_u.configure(state="disabled")
                self.Entry_Trace_Power.configure(state="disabled")
            
        D_Yloc=D_Yloc+D_dY
        self.Trace_Button = Button(trace_window,text="Contornar limite com o cabeçote",command=Close_and_Send_Click)
        self.Trace_Button.place(x=xd_label_L, y=D_Yloc, width=w_label, height=23)
        
        self.Entry_Trace_Speed = Entry(trace_window,width="15")
        self.Entry_Trace_Speed.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        green = "#%02x%02x%02x" % (0, 200, 0)
        self.Entry_Trace_Speed.configure(textvariable=self.trace_speed,justify='center',fg=green)
        trace_variable(self.trace_speed, self.Entry_Trace_Speed_Callback)
        self.entry_set(self.Entry_Trace_Speed,self.Entry_Trace_Speed_Check(),2)
        self.Label_Trace_Speed_u = Label(trace_window,textvariable=self.funits, anchor=W)
        self.Label_Trace_Speed_u.place(x=xd_units_L, y=D_Yloc, width=w_units, height=21)
        
        
        ## Buttons ##
        trace_window.update_idletasks()
        Ybut=int(trace_window.winfo_height())-30
        Xbut=int(trace_window.winfo_width()/2)

        self.Trace_Close = Button(trace_window,text="Cancelar",command=Close_Click)
        self.Trace_Close.place(x=Xbut, y=Ybut, width=130, height=30, anchor="center")
        ################################################################################

    ################################################################################
    #                            EGV Send Window                                   #
    ################################################################################
    def EGV_Send_Window(self,EGV_filename):
        
        egv_send = Toplevel(width=500, height=180)
        egv_send.grab_set() # Use grab_set to prevent user input in the main window during calculations
        egv_send.resizable(0,0)
        egv_send.title('Enviar EGV')
        egv_send.iconname("EGV Send")

        D_Yloc  = 0
        D_dY = 28
        xd_label_L = 12

        w_label=240
        w_entry=40
        w_units=35
        xd_entry_L=xd_label_L+w_label+10
        xd_units_L=xd_entry_L+w_entry+5

        D_Yloc=D_Yloc+D_dY
        self.Label_Preprocess_CRC = Label(egv_send,text="Pré-processar dados CRC")
        self.Label_Preprocess_CRC.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Checkbutton_Preprocess_CRC = Checkbutton(egv_send,text="", anchor=W)
        self.Checkbutton_Preprocess_CRC.place(x=xd_entry_L, y=D_Yloc, width=75, height=23)
        self.Checkbutton_Preprocess_CRC.configure(variable=self.pre_pr_crc)

        D_Yloc=D_Yloc+D_dY
        self.Label_N_EGV_Passes = Label(egv_send,text="Número de passadas EGV")
        self.Label_N_EGV_Passes.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)
        self.Entry_N_EGV_Passes = Entry(egv_send,width="15")
        self.Entry_N_EGV_Passes.place(x=xd_entry_L, y=D_Yloc, width=w_entry, height=23)
        self.Entry_N_EGV_Passes.configure(textvariable=self.n_egv_passes)
        trace_variable(self.n_egv_passes, self.Entry_N_EGV_Passes_Callback)
        self.entry_set(self.Entry_N_EGV_Passes,self.Entry_N_EGV_Passes_Check(),2)

        D_Yloc=D_Yloc+D_dY
        font_entry_width=215
        self.Label_Inkscape_Path = Label(egv_send,text="Arquivo EGV:")
        self.Label_Inkscape_Path.place(x=xd_label_L, y=D_Yloc, width=w_label, height=21)

        EGV_Name = os.path.basename(EGV_filename)
        self.Label_Inkscape_Path = Label(egv_send,text=EGV_Name,anchor="w") #,bg="yellow")
        self.Label_Inkscape_Path.place(x=xd_entry_L, y=D_Yloc, width=200, height=21,anchor="nw")
        
        ## Buttons ##
        egv_send.update_idletasks()
        Ybut=int(egv_send.winfo_height())-30
        Xbut=int(egv_send.winfo_width()/2)

        self.EGV_Close = Button(egv_send,text="Cancelar")
        self.EGV_Close.place(x=Xbut, y=Ybut, width=130, height=30, anchor="e")
        self.EGV_Close.bind("<ButtonRelease-1>", self.Close_Current_Window_Click)

        def Close_and_Send_Click():
            win_id=self.grab_current()
            win_id.destroy()
            self.Open_EGV(EGV_filename, n_passes=int( float(self.n_egv_passes.get()) ))
            
        self.EGV_Send = Button(egv_send,text="Enviar dados EGV",command=Close_and_Send_Click)
        self.EGV_Send.place(x=Xbut, y=Ybut, width=130, height=30, anchor="w")
        ################################################################################
        
        
################################################################################
#             Function for outputting messages to different locations          #
#            depending on what options are enabled                             #
################################################################################
def fmessage(text,newline=True):
    global QUIET
    if (not QUIET):
        if newline==True:
            try:
                sys.stdout.write(text)
                sys.stdout.write("\n")
                debug_message(traceback.format_exc())
            except:
                debug_message(traceback.format_exc())
                pass
        else:
            try:
                sys.stdout.write(text)
                debug_message(traceback.format_exc())
            except:
                debug_message(traceback.format_exc())
                pass

################################################################################
#                               Message Box                                    #
################################################################################
def message_box(title,message):
    title = "%s (K40 Whisperer V%s)" %(title,version)
    if VERSION == 3:
        tkinter.messagebox.showinfo(title,message)
    else:
        tkMessageBox.showinfo(title,message)
        pass

################################################################################
#                          Message Box ask OK/Cancel                           #
################################################################################
def message_ask_ok_cancel(title, mess):
    if VERSION == 3:
        result=tkinter.messagebox.askokcancel(title, mess)
    else:
        result=tkMessageBox.askokcancel(title, mess)
    return result

################################################################################
#                         Debug Message Box                                    #
################################################################################
def debug_message(message):
    global DEBUG
    title = "Debug Message"
    if DEBUG:
        if VERSION == 3:
            tkinter.messagebox.showinfo(title,message)
        else:
            tkMessageBox.showinfo(title,message)
            pass

################################################################################
#                         Choose Units Dialog                                  #
################################################################################
if VERSION < 3:
    import tkSimpleDialog
else:
    import tkinter.simpledialog as tkSimpleDialog

class UnitsDialog(tkSimpleDialog.Dialog):
    def body(self, master):
        self.resizable(0,0)
        self.title('Unidades')
        self.iconname("Units")
        
        self.uom = StringVar()
        self.uom.set("Millimeters")

        Label(master, text="Selecione as unidades de importação do DXF:").grid(row=0)
        Radio_Units_IN = Radiobutton(master,text="Polegadas",      value="Inches")
        Radio_Units_MM = Radiobutton(master,text="Milímetros",     value="Millimeters")
        Radio_Units_CM = Radiobutton(master,text="Centímetros",    value="Centimeters")
        
        Radio_Units_IN.grid(row=1, sticky=W)
        Radio_Units_MM.grid(row=2, sticky=W)
        Radio_Units_CM.grid(row=3, sticky=W)

        Radio_Units_IN.configure(variable=self.uom)
        Radio_Units_MM.configure(variable=self.uom)
        Radio_Units_CM.configure(variable=self.uom)

    def apply(self):
        self.result = self.uom.get()
        return 


class ProjectionDialog(tkSimpleDialog.Dialog):
    def body(self, master):
        self.resizable(0, 0)
        self.title("Projeção DXF")
        self.iconname("DXF Projection")
        self.plane = StringVar()
        self.plane.set("xy")

        Label(
            master,
            text="A geometria não está em um plano principal.\nSelecione a vista para projetar:",
            justify=LEFT,
        ).grid(row=0, column=0, columnspan=2, sticky=W)
        Radiobutton(master, text="Superior (XY)", variable=self.plane, value="xy").grid(row=1, sticky=W)
        Radiobutton(master, text="Frontal (XZ)", variable=self.plane, value="xz").grid(row=2, sticky=W)
        Radiobutton(master, text="Lateral (YZ)", variable=self.plane, value="yz").grid(row=3, sticky=W)

    def apply(self):
        self.result = self.plane.get()
        return

class Stop_ResumeDialog(tkSimpleDialog.Dialog):
    def __init__(self, parent, title):
        self.answer = False
        tkSimpleDialog.Dialog.__init__(self, parent, title) 

    def body(self, frame):
        line1 = "\nSending data to the laser from K40 Whisperer is currently Paused."
        line2 = "Pressione \"Retomar trabalho\" para continuar o trabalho em andamento."
        line3 = "Pressione \"Encerrar trabalho\" para cancelar os trabalhos em execução.\n"
        self.my_line1_label = Label(frame, width=60, text=line1)
        self.my_line1_label.pack()
        self.my_line2_label = Label(frame, width=60, text=line2)
        self.my_line2_label.pack()
        self.my_line3_label = Label(frame, width=60, text=line3)
        self.my_line3_label.pack()
        return frame

    def continue_pressed(self):
        self.answer = False
        self.destroy()

    def cancel_pressed(self):
        self.answer = True
        self.destroy()

    def buttonbox(self):
        self.ok_button = Button(self, text='Retomar trabalho', width=15, command=self.continue_pressed)
        self.ok_button.configure(bg='light green')
        self.ok_button.pack(side="left")
        self.cancel_button = Button(self, text='Encerrar trabalho', width=15, command=self.cancel_pressed)
        self.cancel_button.configure(bg='light coral')
        self.cancel_button.pack(side="right")
        self.bind("<Return>", lambda event: self.continue_pressed())
        self.bind("<Escape>", lambda event: self.cancel_pressed())


        
class toplevel_dummy():
    def winfo_exists(self):
        return False
    
class pxpiDialog(tkSimpleDialog.Dialog):
        
    def __init__(self,
                 parent,
                 units = "mm",
                 SVG_Size            =None,
                 SVG_ViewBox         =None,
                 SVG_inkscape_version=None):

        self.result = None
        self.svg_pxpi   = StringVar()
        self.other      = StringVar()
        self.svg_width  = StringVar()
        self.svg_height = StringVar()
        self.svg_units  = StringVar()
        self.fixed_size = False
        self.svg_units.set(units)
        if units=="mm":
            self.scale=1.0
        else:
            self.scale=1/25.4

        
        ###################################
        ##       Set initial pxpi          #
        ###################################
        pxpi = 72.0
        if SVG_inkscape_version != None:
            if SVG_inkscape_version >=.92:
                pxpi = 96.0
            else:
                pxpi = 90.0
  
        self.svg_pxpi.set("%d"%(pxpi))
        self.other.set("%d"%(pxpi))

        ###################################
        ##       Set minx/miny            #
        ###################################
        if SVG_ViewBox!=None and SVG_ViewBox[0]!=None and SVG_ViewBox[1]!=None:
            self.minx_pixels = SVG_ViewBox[0]
            self.miny_pixels = SVG_ViewBox[1]
        else:
            self.minx_pixels = 0.0
            self.miny_pixels = 0.0
            
        ###################################
        ##       Set Initial Size         #
        ###################################
        if SVG_Size!=None and SVG_Size[2]!=None and SVG_Size[3]!=None:
            self.width_pixels = SVG_Size[2]
            self.height_pixels = SVG_Size[3]
        elif SVG_ViewBox!=None and SVG_ViewBox[2]!=None and SVG_ViewBox[3]!=None:
            self.width_pixels = SVG_ViewBox[2]
            self.height_pixels = SVG_ViewBox[3]
        else:
            self.width_pixels  = 500.0 
            self.height_pixels = 500.0
        ###################################
        ##       Set Initial Size         #
        ###################################
        if SVG_Size[0]!=None and SVG_Size[1]!=None:
            width  = SVG_Size[0] 
            height = SVG_Size[1]
            self.fixed_size=True
        else:
            width  = self.width_pixels/float(self.svg_pxpi.get())*25.4
            height = self.height_pixels/float(self.svg_pxpi.get())*25.4
            
        self.svg_width.set("%f" %(width*self.scale))
        self.svg_height.set("%f" %(height*self.scale))
        ###################################
        tkSimpleDialog.Dialog.__init__(self, parent) 


    def body(self, master):
        self.resizable(0,0)
        self.title('Escala de importação do SVG:')
        self.iconname("SVG Scale")
        
        ###########################################################################
        def Entry_custom_Check():
            try:
                value = float(self.other.get())
                if  value <= 0.0:
                    return 2 # Value is invalid number
            except:
                return 3     # Value not a number
            return 0         # Value is a valid number
        def Entry_custom_Callback(varName, index, mode):
            if Entry_custom_Check() > 0:
                Entry_Custom_pxpi.configure( bg = 'red' )
            else:
                Entry_Custom_pxpi.configure( bg = 'white' )
                pxpi = float(self.other.get())
                width  = self.width_pixels/pxpi*25.4
                height = self.height_pixels/pxpi*25.4
                if self.fixed_size:
                    pass
                else:
                    Set_Value(width=width*self.scale,height=height*self.scale)
                self.svg_pxpi.set("custom")
        ###################################################
        def Entry_Width_Check():
            try:
                value = float(self.svg_width.get())/self.scale
                if  value <= 0.0:
                    return 2 # Value is invalid number
            except:
                return 3     # Value not a number
            return 0         # Value is a valid number
        def Entry_Width_Callback(varName, index, mode):
            if Entry_Width_Check() > 0:
                Entry_Custom_Width.configure( bg = 'red' )
            else:
                Entry_Custom_Width.configure( bg = 'white' )
                width = float(self.svg_width.get())/self.scale
                pxpi = self.width_pixels*25.4/width
                height = self.height_pixels/pxpi*25.4
                Set_Value(other=pxpi,height=height*self.scale)
                self.svg_pxpi.set("custom")
        ###################################################
        def Entry_Height_Check():
            try:
                value = float(self.svg_height.get())
                if  value <= 0.0:
                    return 2 # Value is invalid number
            except:
                return 3     # Value not a number
            return 0         # Value is a valid number
        def Entry_Height_Callback(varName, index, mode):
            if Entry_Height_Check() > 0:
                Entry_Custom_Height.configure( bg = 'red' )
            else:
                Entry_Custom_Height.configure( bg = 'white' )
                height = float(self.svg_height.get())/self.scale
                pxpi = self.height_pixels*25.4/height
                width = self.width_pixels/pxpi*25.4
                Set_Value(other=pxpi,width=width*self.scale)
                self.svg_pxpi.set("custom")
        ###################################################       
        def SVG_pxpi_callback(varName, index, mode):
            if self.svg_pxpi.get() == "custom":
                try:
                    pxpi=float(self.other.get())
                except:
                    pass
            else:
                pxpi=float(self.svg_pxpi.get())
                width  = self.width_pixels/pxpi*25.4
                height = self.height_pixels/pxpi*25.4
                if self.fixed_size:
                    Set_Value(other=pxpi)
                else:
                    Set_Value(other=pxpi,width=width*self.scale,height=height*self.scale)
                
        ###########################################################################
                    
        def Set_Value(other=None,width=None,height=None):
            trace_delete(self.svg_pxpi   ,self.trace_id_svg_pxpi)
            trace_delete(self.other      ,self.trace_id_pxpi)
            trace_delete(self.svg_width  ,self.trace_id_width)
            trace_delete(self.svg_height ,self.trace_id_height)
            
            self.update_idletasks()
            
            if other != None:
                self.other.set("%f" %(other))
            if width != None:
                self.svg_width.set("%f" %(width))
            if height != None:
                self.svg_height.set("%f" %(height))
            
            self.trace_id_svg_pxpi = trace_variable(self.svg_pxpi  , SVG_pxpi_callback)
            self.trace_id_pxpi     = trace_variable(self.other     , Entry_custom_Callback)
            self.trace_id_width    = trace_variable(self.svg_width , Entry_Width_Callback)
            self.trace_id_height   = trace_variable(self.svg_height, Entry_Height_Callback)
            self.update_idletasks()
            
        ###########################################################################
        t0="This dialog opens if the SVG file you are opening\n"
        t1="does not contain enough information to determine\n"
        t2="the intended physical size of the design.\n"
        t3="Select an SVG Import Scale:\n"
        Title_Text0 = Label(master, text=t0+t1+t2, anchor=W)
        Title_Text1 = Label(master, text=t3, anchor=W)
        
        Radio_SVG_pxpi_96   = Radiobutton(master,text=" 96 units/in", value="96")
        Label_SVG_pxpi_96   = Label(master,text="(arquivo salvo com Inkscape v0.92 ou mais recente)", anchor=W)
        
        Radio_SVG_pxpi_90   = Radiobutton(master,text=" 90 units/in", value="90")
        Label_SVG_pxpi_90   = Label(master,text="(arquivo salvo com Inkscape v0.91 ou anterior)", anchor=W)
        
        Radio_SVG_pxpi_72   = Radiobutton(master,text=" 72 units/in", value="72")
        Label_SVG_pxpi_72   = Label(master,text="(arquivo salvo com Adobe Illustrator)", anchor=W)

        Radio_Res_Custom = Radiobutton(master,text=" Personalizado:", value="custom")
        Bottom_row       = Label(master, text=" ")
        

        Entry_Custom_pxpi   = Entry(master,width="10")
        Entry_Custom_pxpi.configure(textvariable=self.other)
        Label_pxpi_units =  Label(master,text="unidades/pol", anchor=W)
        self.trace_id_pxpi = trace_variable(self.other, Entry_custom_Callback)

        Label_Width =  Label(master,text="Largura", anchor=W)
        Entry_Custom_Width   = Entry(master,width="10")
        Entry_Custom_Width.configure(textvariable=self.svg_width)
        Label_Width_units =  Label(master,textvariable=self.svg_units, anchor=W)
        self.trace_id_width = trace_variable(self.svg_width, Entry_Width_Callback)

        Label_Height =  Label(master,text="Altura", anchor=W)
        Entry_Custom_Height   = Entry(master,width="10")
        Entry_Custom_Height.configure(textvariable=self.svg_height)
        Label_Height_units =  Label(master,textvariable=self.svg_units, anchor=W)
        self.trace_id_height = trace_variable(self.svg_height, Entry_Height_Callback)

        if self.fixed_size == True:
             Entry_Custom_Width.configure(state="disabled")
             Entry_Custom_Height.configure(state="disabled")
        ###########################################################################
        rn=0
        Title_Text0.grid(row=rn,column=0,columnspan=5, sticky=W)
        
        rn=rn+1
        Title_Text1.grid(row=rn,column=0,columnspan=5, sticky=W)

        rn=rn+1
        Radio_SVG_pxpi_96.grid(    row=rn, sticky=W)
        Label_SVG_pxpi_96.grid(    row=rn, column=1,columnspan=50, sticky=W)

        rn=rn+1
        Radio_SVG_pxpi_90.grid(    row=rn, sticky=W)
        Label_SVG_pxpi_90.grid(    row=rn, column=1,columnspan=50, sticky=W)
        
        rn=rn+1
        Radio_SVG_pxpi_72.grid(    row=rn, column=0, sticky=W)
        Label_SVG_pxpi_72.grid(    row=rn, column=1,columnspan=50, sticky=W)
        
        rn=rn+1
        Radio_Res_Custom.grid(    row=rn, column=0, sticky=W)
        Entry_Custom_pxpi.grid(    row=rn, column=1, sticky=E)
        Label_pxpi_units.grid(     row=rn, column=2, sticky=W)
        
        rn=rn+1
        Label_Width.grid(         row=rn, column=0, sticky=E)
        Entry_Custom_Width.grid(  row=rn, column=1, sticky=E)
        Label_Width_units.grid(   row=rn, column=2, sticky=W)

        rn=rn+1
        Label_Height.grid(        row=rn, column=0, sticky=E)
        Entry_Custom_Height.grid( row=rn, column=1, sticky=E)
        Label_Height_units.grid(  row=rn, column=2, sticky=W)

        rn=rn+1
        Bottom_row.grid(row=rn,columnspan=50)

        Radio_SVG_pxpi_96.configure  (variable=self.svg_pxpi)
        Radio_SVG_pxpi_90.configure  (variable=self.svg_pxpi)
        Radio_SVG_pxpi_72.configure  (variable=self.svg_pxpi)
        Radio_Res_Custom.configure  (variable=self.svg_pxpi)
        self.trace_id_svg_pxpi = trace_variable(self.svg_pxpi, SVG_pxpi_callback)
        ###########################################################################
    
    def apply(self):
        width  = float(self.svg_width.get())/self.scale
        height = float(self.svg_height.get())/self.scale
        pxpi    = float(self.other.get())
        viewbox = [self.minx_pixels, self.miny_pixels, width/25.4*pxpi, height/25.4*pxpi]
        self.result = pxpi,viewbox
        return 
        
################################################################################
#                          Startup Application                                 #
################################################################################
    
root = Tk()
app = Application(root)
app.master.title(title_text)
app.master.iconname("K40")
app.master.minsize(1020,625)
app.master.geometry("1020x625")
try:
    try:
        import tkFont
        default_font = tkFont.nametofont("TkDefaultFont")
    except:
        import tkinter.font
        default_font = tkinter.font.nametofont("TkDefaultFont")

    default_font.configure(size=9)
    default_font.configure(family='arial')
    #print(default_font.cget("size"))
    #print(default_font.cget("family"))
except:
    debug_message("Font Set Failed.")

################################## Set Icon  ########################################
Icon_Set=False

try:
    #debug_message("Icon set %s" %(sys.argv[0]))
    root.iconbitmap(default="emblem")
    #debug_message("Icon set worked %s" %(sys.argv[0]))
    Icon_Set=True
except:
    debug_message(traceback.format_exc())
    Icon_Set=False
        
if not Icon_Set:
    try:
        scorch_ico_B64=b'R0lGODlhEAAQAIYAAA\
        AAABAQEBYWFhcXFxsbGyUlJSYmJikpKSwsLC4uLi8vLzExMTMzMzc3Nzg4ODk5OTs7Oz4+PkJCQkRERE\
        VFRUtLS0xMTE5OTlNTU1dXV1xcXGBgYGVlZWhoaGtra3FxcXR0dHh4eICAgISEhI+Pj5mZmZ2dnaKioq\
        Ojo62tra6urrS0tLi4uLm5ub29vcLCwsbGxsjIyMzMzM/Pz9PT09XV1dbW1tjY2Nzc3OHh4eLi4uXl5e\
        fn5+jo6Ovr6+/v7/Hx8fLy8vT09PX19fn5+fv7+/z8/P7+/v///wAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
        AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
        AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
        AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACH5BAEKAEkALAAAAAAQABAAQAj/AJMIFBhBQYAACRIkWbgwAA\
        4kEFEECACAxBAkGH8ESEKgBZIiAIQECBAjAA8kNwIkScKgQhAkRggAIJACCZIaJxgk2clgAY4OAAoEAO\
        ABCIIDSZIwkIHEBw0YFAAA6IGDCBIkLAhMyICka9cAKZCIRTLEBIMkaA0MSNGjSBEVIgpESEK3LgMCI1\
        aAWCFDA4EDSQInwaDACBEAImLwCAFARw4HFJJcgGADyZEAL3YQcMGBBpIjHx4EeIGkRoMFJgakWADABx\
        IkPwIgcIGkdm0AMJDo1g3jQBIBRZAINyKAwxEkyHEUSMIcwYYbEgwYmQGgyI8SD5Jo327hgIIAAQ5cBs\
        CQpHySgAA7'
        icon_im =PhotoImage(data=scorch_ico_B64, format='gif')
        root.call('wm', 'iconphoto', root._w, '-default', icon_im)
    except:
        pass
#####################################################################################


if LOAD_MSG != "":
    message_box("K40 Whisperer",LOAD_MSG)

opts, args = None, None
pi_mode_requested = False
try:
    opts, args = getopt.getopt(sys.argv[1:], "hpd",["help", "pi", "debug"])
except:
    print('Unable interpret command line options')
    sys.exit()

for option, value in opts:
    if option in ('-h','--help'):
        print(' ')
        print('Usage: python k40_whisperer.py [-h -p]')
        print('-h    : print this help (also --help)')
        print('-p    : Small screen option (for small raspberry pi display) (also --pi)')
        sys.exit()
    elif option in ('-p','--pi'):
        print("pi mode")
        pi_mode_requested = True
        app.master.state("normal")
        app.master.minsize(222,280)
        app.master.geometry("480x320")
    elif option in ('-d','--debug'):
        DEBUG=True

if DEBUG:
    import inspect
debug_message("Debuging is turned on.")

if not pi_mode_requested:
    def maximize_main_window():
        try:
            app.master.state("zoomed")
        except TclError:
            try:
                app.master.attributes("-zoomed", True)
            except TclError:
                pass
    app.master.after_idle(maximize_main_window)
    
root.mainloop()
