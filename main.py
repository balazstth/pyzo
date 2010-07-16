#   Copyright (c) 2010, Almar Klein
#   All rights reserved.
#
#   This file is part of IEP.
#    
#   IEP is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
# 
#   IEP is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
# 
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

""" Module main
This module contains the main frame. Implements the main window.
Also adds some variables to the iep namespace, such as the callLater
function which is also defined here.
"""

import os, sys
import iep

from PyQt4 import QtCore, QtGui
from queue import Queue, Empty


class MainWindow(QtGui.QMainWindow):
    
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        
        # Store myself
        iep.main = self
        
        # Init dockwidget settings
        self.setTabPosition(QtCore.Qt.AllDockWidgetAreas, QtGui.QTabWidget.West)
        self.setDockOptions(
                QtGui.QMainWindow.AllowNestedDocks
            |  QtGui.QMainWindow.AllowTabbedDocks
            #|  QtGui.QMainWindow.AnimatedDocks
            )
        
        # Set window atrributes
        self.setAttribute(QtCore.Qt.WA_AlwaysShowToolTips, True)
        
        # Set layout as it was the previous time
        if iep.config.state.windowPos:
            self.move(*iep.config.state.windowPos)
        if iep.config.state.windowSize:
            self.resize(*iep.config.state.windowSize)
        if iep.config.state.windowMaximized:
            self.setWindowState(QtCore.Qt.WindowMaximized)
        
        # Construct icon
        pjoin = os.path.join
        iconDir = pjoin(iep.iepDir,'icons')
        iep.icon = QtGui.QIcon()
        iep.icon.addFile(pjoin(iconDir,'iep16.png'), QtCore.QSize(16,16), 0, 0)
        iep.icon.addFile(pjoin(iconDir,'iep32.png'), QtCore.QSize(32,32), 0, 0)
        iep.icon.addFile(pjoin(iconDir,'iep48.png'), QtCore.QSize(48,48), 0, 0)
        
        # Set label and icon
        self.setWindowTitle("IEP (loading ...)")
        self.setWindowIcon(iep.icon)
        
        # Create frame with the IEP logo as a bg (kinda splash screen)
        iconUrl = pjoin(iconDir, 'iep256.png').replace('\\', '/')
        values = [  'image: url({})'.format(iconUrl), 'repeat: no-repeat',
                    'position: center', 'color: #444']
        ss = ' '.join(['background-'+v+';' for v in values])
        self.setStyleSheet( 'QMainWindow {' + ss + '} ')
        
        # Show empty window
        self.show()
        QtGui.qApp.processEvents()
        self.setUpdatesEnabled(False)
        
        # Fill the window
        self.init1()
        
        # Show finally         
        self.setStyleSheet('')
        self.show()
        self.setUpdatesEnabled(True)
        callLater(self.restoreWindowState)
    
    
    def init1(self):
        
        # Delayed imports
        from editorStack import EditorStack
        from shellStack import ShellStack
        from menu import MenuHelper
        import codeparser

        # Create "global" parser instance
        if iep.parser is None:
            iep.parser = codeparser.Parser()
            iep.parser.start()
        
        # Create editor stack and make the central widget
        iep.editors = EditorStack(self)
        self.setCentralWidget(iep.editors)
        
        # Create floater for shell
        dock = QtGui.QDockWidget("Shells", self)
        dock.setObjectName('shells')
        dock.setFeatures(QtGui.QDockWidget.DockWidgetMovable)
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, dock)
        
        # Insert shell stack and add the default shell
        iep.shells = ShellStack(self)
        dock.setWidget(iep.shells)
        iep.shells.addShell()
        
        # Create statusbar and menu 
        # (keep a ref to the menuhelper so it is not destroyed)
        if iep.config.view.showStatusbar:
            iep.status = self.statusBar()
        else:
            iep.status = None
            self.setStatusBar(None)
        self._menuhelper = MenuHelper(self.menuBar())
    
    
    def saveWindowState(self):
        """ Save which tools are loaded and all window positions. """
        import base64
        
        # store window position
        if self.windowState() == QtCore.Qt.WindowMaximized:
            iep.config.state.windowMaximized = 1
            # left,right, width, height stored when maximized
        else:
            iep.config.state.windowMaximized = 0 
            iep.config.state.windowPos = self.x(), self.y()
            iep.config.state.windowSize = self.width(), self.height()
        
        # Save tool list
        tools = iep.toolManager.getLoadedTools()
        iep.config.state.loadedTools = tools
        
        # Get state and make unicode string
        state = bytes(self.saveState())
        state = base64.encodebytes(state).decode('ascii')
        iep.config.state.windowState = state
    
    
    def restoreWindowState(self):
        """ Restore toolss and positions of all windows. """
        import base64
        
        # Obtain default style
        app = QtGui.qApp
        iep.defaultQtStyleName = str(app.style().objectName())
        if sys.platform.startswith('win'):
            iep.defaultQtStyleName = 'cleanlooks' # Windows theme==ugly
            if not iep.config.view.qtstyle:
                iep.config.view.qtstyle = 'cleanlooks' 
        
        # Set qt style and obtain style name of the default style
        qstyle = app.setStyle(iep.config.view.qtstyle)
        if qstyle:
            # We succeeded in setting the style
            app.setPalette(QtGui.QStyle.standardPalette(qstyle))
        else:
            # We still have the default style
            iep.config.view.qtstyle = iep.defaultQtStyleName 
        
        # Load toolss
        if iep.config.state.loadedTools:            
            for toolId in iep.config.state.loadedTools:
                iep.toolManager.loadTool(toolId)
        
        # Restore state
        if iep.config.state.windowState:
            state = iep.config.state.windowState
            state = base64.decodebytes(state.encode('ascii'))
            self.restoreState(state)        
    
    
    def changeEvent(self, event):
        
        # Capture window state change events
        if event.type() == QtCore.QEvent.WindowStateChange:
            ok = [QtCore.Qt.WindowNoState, QtCore.Qt.WindowActive]
            if event.oldState() in ok:
                # Store layout if now non-maximized
                iep.config.state.windowPos = self.x(), self.y()
                iep.config.state.windowSize = self.width(), self.height()
        
        # Proceed normally
        QtGui.QMainWindow.changeEvent(self, event)
    
    
    def closeEvent(self, event):
        """ Override close event handler. """
        
        # Save settings
        iep.saveConfig()
        
        # Proceed with closing...
        result = iep.editors.closeAll()
        if not result:
            self._didClose = False
            event.ignore()
            return
        else:
            self._didClose = True
            event.accept()
        
        # Proceed with closing shells
        for shell in iep.shells:
            shell.terminateNow()
    
    
    def restart(self):
        """ Restart IEP. """
        
        # Close
        self.close()
        
        if self._didClose:
            # Get args
            args = [arg for arg in sys.argv]
            
            # Prepend the executable name (required on Linux somehow)
            lastBit = os.path.basename(sys.executable)
            args.insert(0, lastBit)
            
            # Replace the process! 
            print('restarting',os.getcwd())
            os.execv(sys.executable,args)



class _CallbackEventHandler(QtCore.QObject):
    """ Helper class to provide the callLater function. 
    """
    
    def __init__(self):
        QtCore.QObject.__init__(self)
        self.queue = Queue()

    def customEvent(self, event):
        while True:
            try:
                callback, args = self.queue.get_nowait()
            except Empty:
                break
            try:
                callback(*args)
            except Exception as why:
                print('callback failed: {}:\n{}'.format(callback, why))

    def postEventWithCallback(self, callback, *args):
        self.queue.put((callback, args))
        QtGui.qApp.postEvent(self, QtCore.QEvent(QtCore.QEvent.User))

def callLater(callback, *args):
    """ callLater(callback, *args)
    Post a callback to be called in the main thread. 
    """
    _callbackEventHandler.postEventWithCallback(callback, *args)
    
# Create callback event handler instance and insert function in IEP namespace
_callbackEventHandler = _CallbackEventHandler()   
iep.callLater = callLater

