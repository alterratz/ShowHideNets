# -*- coding: utf-8 -*-

# Copyright (C) 2020 by Bernhard Rieder
# based on WireIt by XESS Corp.

# MIT license
#
# Copyright (C) 2018 by XESS Corp.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from pcbnew import *

import sys
import os
import os.path
import re
import wx
import wx.aui
import wx.lib.filebrowsebutton as FBB

WIDGET_SPACING = 5


original_netlist = {}
hidden_nets = list()


def get_netlist():
    """Create a dict with part ref & pad num as the key and attached net as the value."""
    netlist = {}
    for pad in GetBoard().GetPads():
        pad_key = pad.GetParent().GetReference(), pad.GetPadName()
        netlist[pad_key] = pad.GetNetname(), pad.GetNetCode(), pad.IsConnected()
    return netlist


def get_net_names():
    """Create a list of all the net names in the PCB."""
    return list(set([net[0] for net in get_netlist().values()]))

class LabelledListBox(wx.BoxSizer):
    """ListBox with label."""

    def __init__(self, parent, label, choices, tooltip=""):
        wx.BoxSizer.__init__(self, wx.HORIZONTAL)
        self.lbl = wx.StaticText(parent=parent, label=label)
        self.lbx = wx.ListBox(
            parent=parent,
            choices=choices,
            style = wx.LB_MULTIPLE | wx.LB_NEEDED_SB | wx.LB_SORT,
        )
        self.lbx.SetToolTip(wx.ToolTip(tooltip))
        self.AddSpacer(WIDGET_SPACING)
        self.Add(self.lbl, 0, wx.ALL | wx.ALIGN_TOP)
        self.AddSpacer(WIDGET_SPACING)
        self.Add(self.lbx, 1, wx.ALL | wx.EXPAND)
        self.AddSpacer(WIDGET_SPACING)

    def GetList(self):
        rv = list()
        for i in self.lbx.GetSelections():
            rv.append(self.lbx.GetString(i))
        print(rv)
        return rv


class NetNameDialog(wx.Dialog):
    """Class for getting a new net name from the user."""

    def __init__(self, *args, **kwargs):
        wx.Dialog.__init__(self, None, title=kwargs.get("title"))

        panel = wx.Panel(self)

        self.name_field = LabelledListBox(
            panel, "Net Name:", kwargs.get("net_name_choices"), kwargs.get("tool_tip")
        )

        self.ok_btn = wx.Button(panel, label="OK")
        self.cancel_btn = wx.Button(panel, label="Cancel")
        self.ok_btn.Bind(wx.EVT_BUTTON, self.set_net_name, self.ok_btn)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.cancel, self.cancel_btn)

        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        btn_sizer.AddSpacer(WIDGET_SPACING)
        btn_sizer.Add(self.ok_btn, flag=wx.ALL | wx.ALIGN_CENTER)
        btn_sizer.AddSpacer(WIDGET_SPACING)
        btn_sizer.Add(self.cancel_btn, flag=wx.ALL | wx.ALIGN_CENTER)
        btn_sizer.AddSpacer(WIDGET_SPACING)

        # Create a vertical sizer to hold everything in the panel.
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.name_field, 0, wx.ALL | wx.EXPAND, WIDGET_SPACING)
        sizer.Add(btn_sizer, 0, wx.ALL | wx.ALIGN_CENTER, WIDGET_SPACING)

        # Size the panel.
        panel.SetSizer(sizer)
        panel.Layout()
        panel.Fit()

        # Finally, size the frame that holds the panel.
        self.Fit()

        # Show the dialog box.
        self.ShowModal()

    def set_net_name(self, evt):
        self.netlist = self.name_field.GetList()
        self.Close()

    def cancel(self, evt):
        self.netlist = list()
        self.Close()

    def GetList(self):
        return self.netlist




def hide_net_callback(evt):
    """Hide a Net."""
    allnets=get_net_names()
    allnets.remove('')
    net_names = NetNameDialog(
            title="Attach Pads to New or Existing Net",
            tool_tip="Type or select name for the net to connect these pads.",
            net_name_choices=allnets,
            edit=False,
        )

    for netname in net_names.GetList():
        brd = GetBoard()
        cnct = brd.GetConnectivity()
        for pad in brd.GetPads():
            if pad.GetNetname() == netname:
                cnct.Remove(pad)
                pad.SetNetCode(0)
        hidden_nets.append(netname)

    # Update the board to show the removed connections.
    brd.BuildListOfNets()
    cnct.RecalculateRatsnest()
    Refresh()


def show_net_callback(evt):
    """Show a previously hidden net."""
    if len(hidden_nets) <= 0:
        return

    net_names = NetNameDialog(
            title="Attach Pads to New or Existing Net",
            tool_tip="Type or select name for the net to connect these pads.",
            net_name_choices=hidden_nets,
            edit=False,
        )

    for netname in net_names.GetList():
        # Get the selected pads.
        brd = GetBoard()
        cnct = brd.GetConnectivity()
        for pad in brd.GetPads():
            pad_key = pad.GetParent().GetReference(), pad.GetPadName()
            if original_netlist[pad_key][0] == netname:
                cnct.Add(pad)
                pad.SetNetCode(original_netlist[pad_key][1])
        hidden_nets.remove(netname)

    # Update the board to show the removed connections.
    brd.BuildListOfNets()
    cnct.RecalculateRatsnest()
    Refresh()


def show_all_nets_callback(evt):
    """Show all hidden Nets."""
    if len(hidden_nets) <= 0:
        return

    # Get the selected pads.
    brd = GetBoard()
    cnct = brd.GetConnectivity()
    for pad in brd.GetPads():
        pad_key = pad.GetParent().GetReference(), pad.GetPadName()
        if original_netlist[pad_key][0] in hidden_nets:
            cnct.Add(pad)
            pad.SetNetCode(original_netlist[pad_key][1])

    # Update the board to show the removed connections.
    brd.BuildListOfNets()
    cnct.RecalculateRatsnest()
    Refresh()
    hidden_nets.clear()





class ShowHideNets(ActionPlugin):
    """Plugin class for tools to change wiring between pads"""

    buttons = False  # Buttons currently not installed in toolbar.

    def defaults(self):
        self.name = "ShowHideNets"
        self.category = "Layout"
        self.description = "Show/Hide complete nets/airwires."
        self.icon_file_name = os.path.join(os.path.dirname(__file__), 'show_hide_net.png')

    def Run(self):

        # Add Wire-It buttons to toolbar if they aren't there already.
        if not self.buttons:

            def findPcbnewWindow():
                """Find the window for the PCBNEW application."""
                windows = wx.GetTopLevelWindows()
                pcbnew = [w for w in windows if "Pcbnew" in w.GetTitle()]
                if len(pcbnew) != 1:
                    raise Exception("Cannot find pcbnew window from title matching!")
                return pcbnew[0]

            try:
                # Find the toolbar in the PCBNEW window.
                import inspect
                import os

                filename = inspect.getframeinfo(inspect.currentframe()).filename
                path = os.path.dirname(os.path.abspath(filename))
                pcbwin = findPcbnewWindow()
                top_toolbar = pcbwin.FindWindowById(ID_H_TOOLBAR+1)

                # Add wire-creation button to toolbar.
                hide_button = wx.NewId()
                hide_button_bm = wx.Bitmap(
                    os.path.join(os.path.dirname(__file__), "hide.png"),
                    wx.BITMAP_TYPE_PNG,
                )
                top_toolbar.AddTool(
                    hide_button,
                    "Hide",
                    hide_button_bm,
                    "Hide a Net",
                    wx.ITEM_NORMAL,
                )
                top_toolbar.Bind(wx.EVT_TOOL, hide_net_callback, id=hide_button)

                # Add wire-removal button.
                show_button = wx.NewId()
                show_button_bm = wx.Bitmap(
                    os.path.join(os.path.dirname(__file__), "show.png"), wx.BITMAP_TYPE_PNG
                )
                top_toolbar.AddTool(
                    show_button,
                    "Show Net",
                    show_button_bm,
                    "Show a previously hidden net",
                    wx.ITEM_NORMAL,
                )
                top_toolbar.Bind(wx.EVT_TOOL, show_net_callback, id=show_button)

                # Add pad-swap button.
                show_all_button = wx.NewId()
                show_all_button_bm = wx.Bitmap(
                    os.path.join(os.path.dirname(__file__),"show_all.png"),
                    wx.BITMAP_TYPE_PNG,
                )
                top_toolbar.AddTool(
                    show_all_button,
                    "Show all Nets",
                    show_all_button_bm,
                    "Show all hidden Nets",
                    wx.ITEM_NORMAL,
                )
                top_toolbar.Bind(wx.EVT_TOOL, show_all_nets_callback, id=show_all_button)

                top_toolbar.Realize()

                self.buttons = True  # Buttons now installed in toolbar.

                # Also, store the current netlist to compare against later when dumping wiring changes.
                global original_netlist
                original_netlist = get_netlist()

            except Exception as e:
                debug_dialog("Something went wrong!", e)

