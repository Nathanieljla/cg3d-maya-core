"""
Drag-n-drop this into a maya viewport to install the packages
"""
import os
import re
import time
import platform
import sys
import webbrowser
import base64
#import math
#from datetime import datetime, timedelta
import glob
import tempfile
import shutil
import sys
import subprocess
from os.path import expanduser
import zipfile
from functools import partial
import site

try:
    #python3
    from urllib.request import urlopen
except:
    #python2
    from urllib import urlopen

try:
    #python2
    reload
except:
    #python3
    from importlib import reload

try:
    import maya.utils
    import maya.cmds
    from maya import OpenMayaUI as omui
    
    from PySide2.QtCore import *
    from PySide2.QtWidgets import *
    from PySide2.QtGui import *
    from shiboken2 import wrapInstance
    MAYA_RUNNING = True
except ImportError:
    MAYA_RUNNING = False
    

RESOURCES = None
    
class Platforms(object):
    OSX = 0,
    LINUX = 1,
    WINDOWS = 2
    
    @staticmethod
    def get_name(enum_value):
        if enum_value == Platforms.OSX:
            return 'osx'
        elif enum_value == Platforms.LINUX:
            return 'linux'
        else:
            return 'windows'

        
class ModuleDefinition(object):
    """A .mod file can have multiple entries.  Each definition equates to one entry"""
    
    MODULE_EXPRESSION = r"(?P<action>\+|\-)\s*(MAYAVERSION:(?P<maya_version>\d{4}))?\s*(PLATFORM:(?P<platform>\w+))?\s*(?P<module_name>\w+)\s*(?P<module_version>\d+\.?\d*.?\d*)\s+(?P<module_path>.*)\n(?P<defines>(?P<define>.+(\n?))+)?"
        
    def __init__(self, module_name, module_version,
                 maya_version = '', platform = '',
                 action = '+', module_path = '',
                 defines = [],
                 *args, **kwargs):
        
        self.action = action
        self.module_name = module_name
        self.module_version = module_version
        
        self.module_path = r'.\{0}'.format(self.module_name)
        if module_path:
            self.module_path = module_path

        self.maya_version = maya_version
        if self.maya_version is None:
            self.maya_version = ''
        
        self.platform = platform
        if self.platform is None:
            self.platform = ''
        
        self.defines = defines
        if not self.defines:
            self.defines = []
        
    def __str__(self):
        return_string = '{0} '.format(self.action)
        if self.maya_version:
            return_string += 'MAYAVERSION:{0} '.format(self.maya_version)
            
        if self.platform:
            return_string += 'PLATFORM:{0} '.format(self.platform)
            
        return_string += '{0} {1} {2}\n'.format(self.module_name, self.module_version, self.module_path)
        for define in self.defines:
            if define:
                return_string += '{0}\n'.format(define.rstrip('\n'))
         
        return_string += '\n'    
        return return_string


class ModuleManager(QThread):
    """Used to edit .mod files quickly and easily."""
    
    def __init__(self, module_name, module_version, package_name='',
                 include_site_packages = False):
        
        QThread.__init__(self)
        self.install_succeeded = False
        
        self._module_definitions = []
        self.module_name = module_name
        self.module_version = module_version
        
        self.package_name = package_name
        if not self.package_name:
            self.package_name = self.module_name
        
        self.maya_version = self.get_app_version()
        self.platform = self.get_platform()
        
        
        self.max, self.min, self.patch = ModuleManager.get_python_version()
        
        #common locations
        self._version_specific = self.is_version_specific()  
        self.app_dir = os.getenv('MAYA_APP_DIR')
        self.install_root = self.get_install_root()
        self.relative_module_path = self.get_relative_module_path()
        self.module_path = self.get_module_path()
        self.icons_path = self.get_icon_path()
        self.presets_path = self.get_presets_path()
        self.scripts_path = self.get_scripts_path()
        self.plugins_path = self.get_plugins_path()
        
        self.site_packages_path = self.get_site_package_path()
        if not include_site_packages:
            self.site_packages_path = ''
            
        self.package_install_path = self.get_package_install_path()
        
        #Non-Maya python and pip paths are needed for installing on linux (and OsX?)
        self.python_path, self.pip_path = self.get_python_paths()
        self.command_string, self.uses_global_pip = self.get_command_string()
     
    
    def __del__(self):
        #TODO: Determine why I put a wait on this fuction 
        self.wait()
 

    @staticmethod        
    def get_python_version():
        """Get the running version of python as a tuple of 3 ints"""
        pmax, pmin, patch =  sys.version.split(' ')[0].split('.')
        return( int(pmax), int(pmin), int(patch))
       
       
    @staticmethod
    def get_app_version():
        """What version of Maya is this?"""
        return int(str(maya.cmds.about(apiVersion=True))[:4])
    
    
    @staticmethod
    def get_platform_string(platform):
        """Convert the current Platform value to a Module string"""
        if platform is Platforms.OSX:
            return 'mac'
        elif platform is Platforms.LINUX:
            return 'linux'
        else:
            return 'win64'
    
    
    @staticmethod
    def get_platform():
        result = platform.platform().lower()
        if 'darwin' in result:
            return Platforms.OSX
        elif 'linux' in result:
            return Platforms.LINUX
        elif 'window' in result:
            return Platforms.WINDOWS
        else:
            raise ValueError('Unknown Platform Type:{0}'.format(result))
    
    
    @staticmethod
    def make_folder(folder_path):
        print(folder_path)
        
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)


    @staticmethod
    def get_ui_parent():
        return wrapInstance( int(omui.MQtUtil.mainWindow()), QMainWindow )      
 

    @staticmethod    
    def run_shell_command(cmd, description):
        #NOTE: don't use subprocess.check_output(cmd), because in python 3.6+ this error's with a 120 code.
        print('\n{0}'.format(description))
        print('Calling shell command: {0}'.format(cmd))

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        stdout = stdout.decode()
        stderr = stderr.decode()
        
        print(stdout)
        print(stderr)
        if proc.returncode:
            raise Exception('Command Failed:\nreturn code:{0}\nstderr:\n{1}\n'.format(proc.returncode, stderr))
        
        return(stdout, stderr)
    
        
    @staticmethod
    def get_python_paths():
        """Returns maya's python path and location of a global pip
        
        Note: The pip path might not exist on the system.
        """
        python_path = ''
        pip_path = ''
        pmax, pmin, patch = ModuleManager.get_python_version()
        platform = ModuleManager.get_platform()
        
        version_str = '{0}.{1}'.format(pmax, pmin)
        if platform == Platforms.WINDOWS:
            python_path = os.path.join(os.getenv('MAYA_LOCATION'), 'bin', 'mayapy.exe')
            if pmax > 2:
                #python3 pip path
                pip_path = os.path.join(os.getenv('APPDATA'), 'Python', 'Python{0}{1}'.format(pmax, pmin), 'Scripts', 'pip{0}.exe'.format(version_str))
            else:
                #python2 pip path
                pip_path = os.path.join(os.getenv('APPDATA'), 'Python', 'Scripts', 'pip{0}.exe'.format(version_str))

        elif platform == Platforms.OSX:
            python_path = '/usr/bin/python'
            pip_path = os.path.join( expanduser('~'), 'Library', 'Python', version_str, 'bin', 'pip{0}'.format(version_str) )
     
        elif platform == Platforms.LINUX:
            python_path = os.path.join(os.getenv('MAYA_LOCATION'), 'bin', 'mayapy')
            pip_path = os.path.join( expanduser('~'), '.local', 'bin', 'pip{0}'.format(version_str) )
             
        return (python_path, pip_path)
         
            
    @staticmethod
    def get_command_string():
        """returns a commandline string for launching pip commands
        
        If the end-user is on linux then is sounds like calling pip from Mayapy
        can cause dependencies issues when using a default python install.
        So if the user is on osX or windows OR they're on linux and don't
        have python installed, then we'll use "mayapy -m pip" else we'll
        use the pipX.exe to run our commands.        
        """
        python_path, pip_path = ModuleManager.get_python_paths()
        platform = ModuleManager.get_platform()        

        command = '{0}&-m&pip'.format(python_path)
        global_pip = False
        if platform == Platforms.LINUX:
            try:
                #I don't use "python" here, because on windows that opens the MS store vs. erroring.
                #No clue what it might do on linux
                ModuleManager.run_shell_command(['py'], 'Checking python install')
                command = pip_path
                global_pip = True
            except:
                #Python isn't installed on linux, so the default command is good
                pass
            
        return (command,  global_pip)

                
    @staticmethod
    def pip_install(repo_name, pip_args = [], *args, **kwargs):
        pip_command, global_pip = ModuleManager.get_command_string()
        cmd_str = ('{0}&install&{1}').format(pip_command, repo_name)
        args = cmd_str.split('&') + pip_args
        stdout, stderr = ModuleManager.run_shell_command(args, 'PIP:Installing Package')
        
        return stdout
    
    
    @staticmethod
    def pip_uninstall(repo_name, pip_args = [], *args, **kwargs):
        pip_command, global_pip = ModuleManager.get_command_string()
        cmd_str = ('{0}&uninstall&{1}').format(pip_command, repo_name)
        args = cmd_str.split('&') + pip_args
        stdout, stderr = ModuleManager.run_shell_command(args, 'PIP:Installing Package')
        
        return stdout
    

    @staticmethod
    def pip_list(pip_args = [], *args, **kwargs):
        pip_command, global_pip  = ModuleManager.get_command_string()
        cmd_str = ('{0}&list').format(pip_command)
        args = cmd_str.split('&') + pip_args
        stdout, stderr = ModuleManager.run_shell_command(args, 'PIP:Listing Packages')
        
        return stdout    

    @staticmethod
    def pip_show(repo_name, pip_args = [], *args, **kwargs):
        pip_command, global_pip  = ModuleManager.get_command_string()
        cmd_str = ('{0}&show&{1}').format(pip_command, repo_name)
        args = cmd_str.split('&') + pip_args
        stdout, stderr = ModuleManager.run_shell_command(args, 'PIP:Show Package Info')
        
        return stdout
    
    
    @staticmethod
    def package_installed(package_name):
        """returns True if the repo is already on the system"""
        
        return ModuleManager.pip_list().find(package_name) != -1
    

    @staticmethod
    def package_outdated(package_name):
        """Check to see if a local package is outdated
        
        Checks to see the local pacakge is out-of-date.  This will always
        be true with remote packages that are from Git, but will be accurate
        with packages registered on PyPi. Since package_outdated()
        assumes the package exists before checking make sure you you first
        check the existance of the package with package_installed() before
        checking the outdated status.
        
        Returns:
        --------
        bool
            True if missing or outdated, else False
        """
        #TODO: get version checking to work with git packages.
        #https://stackoverflow.com/questions/11560056/pip-freeze-does-not-show-repository-paths-for-requirements-file
        #https://github.com/pypa/pip/issues/609
        #it looks like we'd have to install packages with pip -e for this to work,
        #but then we can't install to a target dir. I'm getting errors about
        #trying to install in maya/src, but --user doesn't work either.

        #I'm using --uptodate here, because both --uptodate and --outdated
        #will be missing the package if the pacakage isn't registered with PyPi
        #so -uptodate is easier to verify with than -o with remote package that
        # might or might not be registered with PyPi
        
              
        result = ModuleManager.pip_list(pip_args =['--uptodate'])
        outdated = result.find(package_name) == -1
        if outdated:
            return True
        else:
            return False
    
    
    #def get_pip_list(self, *args, **kwargs):
        #result = Custom_Installer.pip_list(*args, **kwargs)
        #return result
        
    
    #def get_pip_show(self, *args, **kwargs):
        #result = Custom_Installer.pip_show(self.package_name, *args, **kwargs)
        #return result
    

    def install_remote_package(self, package_name = '', to_module = True):
        if not package_name:
            package_name = self.get_remote_package()
        
        #https://stackoverflow.com/questions/39365080/pip-install-editable-with-a-vcs-url
        #github = r'https://github.com/Nathanieljla/fSpy-Maya.git'
        
        pip_args = []
        if to_module:
            pip_args = [
                #r'--user', 
                #r'--editable=git+{0}#egg={1}'.format(github, self.repo_name), 
                r'--target={0}'.format(self.scripts_path), 
            ]
        self.pip_install(package_name, pip_args)
    
    
    def get_remote_package(self):
        """returns the github or PyPi name needed for installing"""
        maya.cmds.error( "No Package name/github path defined.  User needs to override Module_manager.get_remote_package()" )

        
    def __ensure_pip_exists(self):
        """Make sure OS level pip is installed
        
        This is written to work with all platforms, but
        I've updated this to only run when we're on linux
        because it sounds like that's the only time it's needed
        """
        
        if not self.uses_global_pip:
            print("Using Maya's PIP")
            return
        
        if os.path.exists(self.pip_path):
            print('Global PIP found')
            return
        
        tmpdir = tempfile.mkdtemp()
        get_pip_path = os.path.join(tmpdir, 'get-pip.py')
        print(get_pip_path)
        
        if self.platform == Platforms.OSX:
            #cmd = 'curl https://bootstrap.pypa.io/pip/{0}/get-pip.py -o {1}'.format(pip_folder, pip_installer).split(' ')
            cmd = 'curl https://bootstrap.pypa.io/pip/get-pip.py -o {0}'.format(get_pip_path).split(' ')
            self.run_shell_command(cmd, 'get-pip')

        else:
            # this should be using secure https, but we should be fine for now
            # as we are only reading data, but might be a possible mid attack
            #response = urlopen('https://bootstrap.pypa.io/pip/{0}/get-pip.py'.format(pip_folder))
            response = urlopen('https://bootstrap.pypa.io/pip/get-pip.py')
            data = response.read()
            
            with open(get_pip_path, 'wb') as f:
                f.write(data)
                
        # Install pip
        # On Linux installing pip with Maya Python creates unwanted dependencies to Mayas Python version, so pip might not work 
        # outside of Maya Python anymore. So lets install pip with the os python version. 
        filepath, filename = os.path.split(get_pip_path)
        #is this an insert, so this pip is found before any other ones?
        sys.path.insert(0, filepath)
        
        
        if self.platform == Platforms.OSX or self.platform == Platforms.LINUX:
            python_str = 'python{0}.{1}'.format(self.max, self.min)
        else:
            python_str = self.python_path
            
        cmd = '{0}&{1}&--user&pip'.format(python_str, get_pip_path).split('&')
        self.run_shell_command(cmd, 'install pip')
        
        print('Global PIP is ready for use!')
        
        
    def is_version_specific(self):
        """Is this install for a specific version of Maya?
        
        Some modules might have specific code for different versions of Maya.
        For example if Maya is running Python 3 versus. 2. get_relative_module_path()
        returns a different result when this True vs.False unless overridden by
        the user.
        
        Returns:
        --------
        bool
            False
        """        
        
        return False
     
    def get_install_root(self):
        """Where should the module's folder and defintion install?
        
        Maya has specific locations it looks for module defintitions os.getenv('MAYA_APP_DIR')
        For windows this is "documents/maya/modules" or "documents/maya/mayaVersion/modules"
        However 'userSetup' files can define alternative locations, which is
        good for shared modules in a production environment.
        
        Returns:
        --------
        str
            os.path.join(self.app_dir, 'modules')
        """        
        return os.path.join(self.app_dir, 'modules')
    
    def get_relative_module_path(self):
        """What's the module folder path from the install root?
        
        From the install location we can create a series of folder to reach
        the base of our module.  This is where Maya will look for the
        'plug-ins', 'scripts', 'icons', and 'presets' dir.  At a minimum
        you should return the name of your module. The default implementation
        create as a path of 'module-name'/platforms/maya-version/platform-name/x64
        when is_version_specific() returns True
        
        Returns:
        str
            self.module_name when is_version_specific() is False
        
        """
        root = self.module_name
        if self._version_specific:
            root = os.path.join(self.module_name, 'platforms', str(self.maya_version),
                                Platforms.get_name(self.platform),'x64')  
        return root
    
    def get_module_path(self):
        return os.path.join(self.install_root, self.relative_module_path)
    
    def get_icon_path(self):
        return os.path.join(self.module_path, 'icons')
    
    def get_presets_path(self):
        return os.path.join(self.module_path, 'presets')
    
    def get_scripts_path(self):
        return os.path.join(self.module_path, 'scripts')
    
    def get_plugins_path(self):
        return os.path.join(self.module_path, 'plug-ins')
    
    def get_site_package_path(self):
        return os.path.join(self.scripts_path, 'site-packages')
    
    def get_package_install_path(self):
        return os.path.join(self.scripts_path, self.module_name)
    
  
    def read_module_definitions(self, path):
        self._module_definitions = []
        if (os.path.exists(path)):
            file = open(path, 'r')
            text = file.read()
            file.close()
          
            for result in re.finditer(ModuleDefinition.MODULE_EXPRESSION, text):
                resultDict = result.groupdict()
                if resultDict['defines']:
                    resultDict['defines'] = resultDict['defines'].split("\n")
                    
                definition = ModuleDefinition(**resultDict)
                self._module_definitions.append(definition)
      
                        
    def write_module_definitions(self, path):
        file = open(path, 'w')
        for entry in self._module_definitions:
            file.write(str(entry))
        
        file.close()

                           
    def __get_definitions(self, search_list, key, value):
        results = []
        for item in search_list:
            if item.__dict__[key] == value:
                results.append(item)
                
        return results
        
          
    def _get_definitions(self, *args, **kwargs):
        result_list = self._module_definitions
        for i in kwargs:
            result_list = self.__get_definitions(result_list, i, kwargs[i])
        return result_list
    
    
    def remove_definitions(self, *args, **kwargs):
        """
        removes all definitions that match the input argument values
        example : module_manager_instance.remove_definitions(module_name='generic', platform='win', maya_version='2023')
        
        Returns:
        --------
        list
            the results that were removed from the manager.
        
        """ 
        results = self._get_definitions(**kwargs)
        for result in results:
            self._module_definitions.pop(self._module_definitions.index(result))
            
        return results
    
    
    def remove_definition(self, entry):
        self.remove_definitions(module_name=entry.module_name,
                                platform=entry.platform, maya_version=entry.maya_version)
    
    def add_definition(self, definition):
        """

        """
        #TODO: Add some checks to make sure the definition doesn't conflict with an existing definition
        self._module_definitions.append(definition)
        
   
    def run(self):
        """this starts the QThread"""
        try:
            self.install_succeeded = self.install()
        except Exception as e:
            self.install_succeeded = False
            print('Install Failed!!\n{0}'.format(e))
            
                 
    def get_definition_entry(self):
        """Converts this class into a module_defintion
        
        Returns:
        --------
        Module_definition
            The module defintion that represents the data of the Module_manager
        
        """
        maya_version = str(self.maya_version)
        relative_path = '.\{0}'.format(self.relative_module_path)        
        platform_name =  self.get_platform_string(self.get_platform())
        
        if not self._version_specific:
            maya_version = ''
            platform_name = ''
            
        defines = []
        if self.site_packages_path:
            site_path =  'PYTHONPATH+:={0}'.format(self.site_packages_path.split(self.module_path)[1])
            defines = [site_path]
        
        module_definition = ModuleDefinition(self.module_name, self.module_version,
                                                             maya_version=maya_version, platform=platform_name, 
                                                             module_path=relative_path,
                                                             defines=defines)
        return module_definition
     
             
    def update_module_definition(self, filename):
        """remove old defintions and adds the current defintion to the .mod
        
        Returns:
        --------
        bool
            True if the update was successful else False        
        """
        new_entry = self.get_definition_entry()
        self.remove_definition(new_entry) #removes any old entries that might match before adding the new one
        self.add_definition(new_entry)  
        try:
            self.write_module_definitions(filename)
        except IOError:
            return False
        
        return True
        

    def pre_install(self):
        """Called before install() to do any sanity checks and prep
        
        This function attempts to create the required install folders
        and update/add the .mod file. Sub-class should call this function
        when overriding

        Returns:
        --------
        bool
            true if the install can continue
        """
        try:
            self.__ensure_pip_exists()

        except Exception as e:
            print('failed to setup global pip {0}'.format(e))
            return False
        
        try:          
            self.make_folder(self.module_path)       
            self.make_folder(self.icons_path)
            self.make_folder(self.presets_path)
            self.make_folder(self.scripts_path)
            self.make_folder(self.plugins_path)
            
            if self.site_packages_path:
                self.make_folder(self.site_packages_path)
        except OSError:
            return False

        filename = os.path.join(self.install_root, (self.module_name + '.mod'))
        self.read_module_definitions(filename)
              
        return self.update_module_definition(filename)
    

    def install(self):
        """The main install function users should override"""        
        installed = False
        if not self.package_installed(self.package_name):

            try:
                self.install_remote_package()
                installed = True
            except:
                pass
            
        return installed
    
    
    def post_install(self):
        """Used after install() to do any clean-up

        """  
        print('post install')
        if self.install_succeeded:
            if self.scripts_path not in sys.path:
                sys.path.append(self.scripts_path)
                print('Add scripts path [{}] to system paths'.format(self.scripts_path))
            else:
                print('scripts path in system paths')
                
                
    def install_pymel(self):
        """Installs pymel to a common Maya location"""
        if not self.package_installed('pymel'):
            self.pip_install('pymel')
        
    
    
##-----begin UI----##
    
class IconButton(QPushButton):
    def __init__(self, text, highlight=False, icon=None, success=False, *args, **kwargs):
        super(IconButton, self).__init__(QIcon(icon), text, *args, **kwargs)

        self.icon = icon
        self.highlight = highlight
        self.success = success
        self.setMinimumHeight(34)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        if self.highlight:
            font = self.font()
            font.setPointSize(14)
            font.setBold(True)
            self.setFont(font)

        if self.success:
            font = self.font()
            font.setPointSize(14)
            font.setBold(True)
            self.setFont(font)

        if self.icon:
            self.setIconSize(QSize(22, 22))
            self.setIcon(QIcon(self.AlphaImage()))

    def AlphaImage(self):
        if self.highlight and not self.success:
            AlphaImage = QPixmap(self.icon)
            painter = QPainter(AlphaImage)

            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(AlphaImage.rect(), '182828')

            return AlphaImage

        else:
            return QPixmap(self.icon)
        
     

class Resources(object):
    preloaderAnimBase64 = '''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'''
    BYTE_GIF = QByteArray.fromBase64( preloaderAnimBase64.encode() )
    
    company_base64 = None
    install_base64 = '''iVBORw0KGgoAAAANSUhEUgAAAFgAAABYCAYAAABxlTA0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAA2NJREFUeJztnN9RGzEQh3+ryTvuIHQAqSCOzn4OJUAFoYO4BKeCpAR4PkvjdGA6oATTgDYvx4xjwv3x7Z7kyX5v3N5I6w8h6eQ9AMMwDMMwDMMwDMMwDMMwDON/gHIn0JcY4+fDn733v3PlMoTiBdd1feGcewYwO7zOzNvFYvElT1b9cbkT6MI5t8aRXAAgonkI4XuGlAZRvGAANy2x+8myOJFzEPxm9PaMFcE5CD5rTLAyJlgZE6yMCVbGBCtjgpX5oNHoZrP5hr8fEPbOuZX3/kmjv6HEGK9SSuvDa865tff+Ubov8bOIGONXZn74R+g5pXS9XC5fhrQXQuC2eFVVgz5Dc7axA3B5FNoT0Vx6EIhPESml1TuhSyLa1nV9Id1nX+q6viCiLd7KBYDZ8aiWQFwwEV23xXJJfpXbkd9cut/JF7kckvvI1UJcMDNvu+6ZUvIQuX1yH4q4YOfcPYB9131TSB44cvdN7qKIC/bePzVzWVbJQ+Vq7CAApTk4t+RS5AKKi1wuySXJBZR3EVNLLk0uMME2bSrJJcoFJtoHa0suVS4wcV1EjPGq2Wt2flnJzDtmnjvnWn8pKaVZqXKBDIUnQyV3ietzT8PkcoFMlT1DJAuRRS6QsXRqQsnZ5AKZa9MmkJxVLlBA8Z+i5OxygQIEAyqSi5ALFCIYEJVcjFygIMGAiOSi5AKFCQZGSS5OLiAoWLLE/wTJo+VqvaIwWrBWif8AyaPkar+iMPqwR6vEv+cB0eiRq/2KgsRpmlqJfyP59p2w1Jyr+oqChGDVEn/v/SMRXTPz7vUaM29TSpdCC5pq/iq1adI0Ij/lzuMU1A/cY4xX2n2cyvHOQYPRgruKNVJK87F9aJFSap1jJQpRRk8RRPTcEV9tNhsw86+hlZVahBA+MvOaiNoWOBDRri3eh9GCmXnbstIDwIyI1kS0DiGM7U4Mou5HgKYScxQSU8QDenyZeYbsJQqyRwtu/uzF62pzw8wriXZEdhEppfXhPvXcYebdYrH4IdGWiODlcvnCzHON8s+pYeYtM8+l2hM/rgwh/ARwK93uRPyqqupOskHxB42qqu6Y+RZntvAx8720XEDxwL0pZ7oBcNOcihX3rweaKe2hpD26YRiGYRiGYRiGYRiGYRiGYRiGYRjD+AN6etoeN+hk/AAAAABJRU5ErkJggg=='''
    close_base64 = '''iVBORw0KGgoAAAANSUhEUgAAAFgAAABYCAYAAABxlTA0AAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAALEwAACxMBAJqcGAAAA7lJREFUeJztm8tx2zAQhv9lA3YHdiqwO4iGpM5xB6Y7UAdRKohSQeQO5DMfo3Qgd6B0IDfAzSHgjOwhJQDCgvTMfleCXPIbEI8FACiKoiiKoiiKoiiKoiiKoiiKoiiKoijKECT14LqubwAUzDwDACLatW27nM/nb1IxbWia5o6ZF8x8a95rT0SrNE1fJeKJCK7r+ieARc+ldZZlTxIxbSjL8oqItkR0//EaEd1LSA4u2NSQ3Yki67ZtF7Frcl3XN8y86ZNr2GdZ9iV03CT0A5n54UyRgoi2ZVlehY49RNM0dwB2J+QCwK1EbAnBh3NliOg+lmTzR20BXEvH6iO44CRJtjblYkh2kXumWfMmuOA0TV+ZeWNTlojukyTZm184KFVVPRpptjV3HfodAAHBAMDMhUONuGbmbUjJVVU9EtHa4ZZ1nue/QsU/RkTwfD5/Y+aZ+T1tCCbZQ+5KcugoNtHoqOv6N4DCsviBmRd5nj97xhoaf/fCzIVvLFvEBQPOkr0+PEYMH6IIBmQFTFUuEFEw4NU+LrMs+zF00Ux910R0bnLTcSCimVTeoY+oggG/Hr6vEzqVVxggulxgBMHA5ZI/i1xgJMEA0DTNVzMhsZ4ItG27SJLk+kzS5h3MvCOihyzL/vq/rT+jCQbc8wRG1q1LeWaejZmDHlUwIJeMmYJcQGgm50Kapq9ENAuZbGHmzRTkAhOowR0eHdcQo66afGQygoEgkiclF5hAE3GMR5LoGNGkjS+TEgz8l0xEW8fbDh73RGFSTQTgnlc4JmaOwZZJCb5EbsfUJE9CcFmWV0mSrHCh3A6TUxZZoXBldMEBh2cfmcSIYtROzidp4/D4wjQ5ozKaYFe5Jg8xM7lfW9GjSx6lifBJ8hxPfS+9PybRBYeS81kkR20iPKRsh6R0SSIAe5tnxdyu9S5urEBmFWMFhwS7zSjAo6PcE9FDrNWNKIJDrcMNMeUlJHHB0nI7pipZVHBd198BLG3Lh5jmuu4kIqIiTdOXS2KeQvKMxmibQaa0EUVEsGuzIPGBrpJNxxe8JosM04hoaVn0QEQzidqTZdkTM1tvBGzbdhn6HQABwVVVPcLuvEPXyfwJ/Q4deZ7/YubCpqxAsgmAgGCzb+Ec0YZJeZ4/20qWQELwyeMDXdIm5jamPM+fLZJEe4nYImc0AKz6rnX5gDH2iKVp+mKm1n2S9w47NJ0QG6Y1TfOtbdvjTmbNzJuxN4P0HPHdj3EwUlEURVEURVEURVEURVEURVEURVEURVGAf9l4XANGvwF5AAAAAElFTkSuQmCC'''

    def __init__(self):
        super(Resources, self).__init__()        
        self.installer = None
        
    def __del__(self):
        if self.installer:
            self.installer.deleteLater()
             
    @staticmethod
    def base64_to_QPixmap(base64Image):
        pixmap = QPixmap()
        byte_array =  QByteArray.fromBase64( base64Image.encode() )
        pixmap.loadFromData(byte_array)
        
        return QPixmap(pixmap)
    
    @staticmethod
    def qPixmap_to_base64(pixmap, extension):
        #https://doc.qt.io/qtforpython/index.html
        #https://forum.qt.io/topic/85064/qbytearray-to-string/2
        image = pixmap.toImage()
        byteArray = QByteArray()
        buffer = QBuffer(byteArray)
        image.save(buffer, "png")
        base64 = byteArray.toBase64().data()
        result = str(base64, encoding='utf-8')
            
        return result
            
    @staticmethod
    def file_to_base64(file_path):
        extension = os.path.basename(file_path).split('.')[-1]
        pixmap = QPixmap()
        if pixmap.load(file_path):
            return Resources.qPixmap_to_base64(pixmap, extension)
        else:
            return ''
        
    @staticmethod
    def print_file_string(image_path):
        image_string =  Resources.file_to_base64(image_path)
        if image_string:
            print ("Use the next line for the Resources.company_base64")
            print(image_string)
  
      
    def set_installer(self, installer):
        self.installer = installer
    
    
    @property
    def close_icon(self):        
        return self.base64_to_QPixmap(Resources.close_base64)
    
    @property
    def install_icon(self):        
        return self.base64_to_QPixmap(Resources.install_base64)
              
    @property
    def company_icon(self):
        result = None
        if Resources.company_base64:
            result = self.base64_to_QPixmap(Resources.company_base64)
        
        return result
    
    @company_icon.setter
    def company_icon(self, value):
        Resources.company_base64 = value
      
    
class InstallerUi(QWidget):
    def __init__(self, name, module_manager, background_color = '',
                 company_logo_size = [64, 64],
                 launch_message='', 
                 installing_message = 'Installing, please wait ...',
                 failed_message='Install Failed!',
                 success_message="Install Completed Successfully!",
                 post_error_messsage='Install Successful. Clean-up errored.  See output.', 
                 *args, **kwargs
                 ):
        
        parent = module_manager.get_ui_parent()
        super(InstallerUi, self).__init__(parent=parent, *args, **kwargs)
        
        self.name = name
        self.module_manager = module_manager
        
        self.launch_message = launch_message
        self.installing_message = installing_message
        self.failed_message = failed_message
        self.success_message = success_message
        self.post_error_messsage =  post_error_messsage
        
        self.create_layout(background_color, company_logo_size)
        self.set_default_size(name)
        self.install_button.clicked.connect(self.on_install)
        self.close_button.clicked.connect(self.on_close)
        #

    def set_default_size(self, name):
        self.animated_gif.hide()         
        self.setObjectName(name)
        self.setWindowTitle(name)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowFlags(Qt.Tool)
        self.setFixedSize(self.layout().minimumSize())
        self.close_button.hide()
        
        size = self.layout().minimumSize()
        width = size.width()
        height = size.height()
        desktop = QApplication.desktop()
        screenNumber = desktop.screenNumber(QCursor.pos())
        screenRect = desktop.screenGeometry(screenNumber)
        widthCenter = (screenRect.width() / 2) - (width / 2)
        heightCenter = (screenRect.height() / 2) - (height / 2)        
        self.setGeometry(QRect(widthCenter, heightCenter, width, height))
        
        
    def create_layout(self, background_color, company_logo_size):
        #background color
        if background_color:
            palette = self.palette()
            palette.setColor(self.backgroundRole(), background_color)
            self.setPalette(palette)             
        
        ##-----create all our ui elements THEN arrange them----##
        logo = None

        if RESOURCES.company_icon is not None:
            logo = QLabel()
            smallLogo = RESOURCES.company_icon.scaled(company_logo_size[0], company_logo_size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation)
    
            logo.setPixmap(smallLogo)
            logo.setAlignment(Qt.AlignCenter | Qt.AlignCenter)
            logo.setMargin(15)

        self.install_button = IconButton('Install', highlight=True) #, icon=RESOURCES.install_icon)
        self.install_button.setMinimumHeight(42)
        self.close_button = IconButton(' Close', icon=RESOURCES.close_icon)
        self.close_button.setMinimumHeight(42)

        self.message_label = QLabel()
        self.message_label.setText(self.launch_message)
        self.message_label.show()
        
        self.movie = QMovie()
        self.device = QBuffer(Resources.BYTE_GIF)
        self.movie.setDevice(self.device)
        self.animated_gif = QLabel()

        self.animated_gif.setMovie(self.movie)
        self.animated_gif.setMaximumHeight(24)
        self.animated_gif.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.animated_gif.setScaledContents(True)
        self.animated_gif.setMaximumWidth(24)
        outer = QVBoxLayout()
        self.setLayout(outer)
        if logo:
            outer.addWidget(logo, 0)
            
        message_layout = QVBoxLayout()
        message_layout.addWidget(self.message_label, 1)
        message_layout.setAlignment(Qt.AlignCenter)
        outer.addLayout(message_layout)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.install_button, 0)
        button_layout.addWidget(self.close_button, 0)
        button_layout.addWidget(self.animated_gif, 0)
        button_layout.addStretch()
        button_layout.setAlignment(Qt.AlignCenter)

        outer.addLayout(button_layout)
        self.layout()
                
    def on_install(self):
        self.install_button.hide()
        #self.movie.start() #I'm thinking this causes maya to crash when debugging in WING
        self.animated_gif.show()
        self.message_label.setText(self.installing_message)
        self.message_label.show()
        
        if self.module_manager.pre_install():
            self.connect(self.module_manager, SIGNAL('finished()'), self.done)
            self.module_manager.start()
        
    
    def done(self):
        self.close_button.show()
        self.animated_gif.hide()
        if self.module_manager.install_succeeded:
            self.message_label.setText(self.success_message)
        else:
            self.message_label.setText(self.failed_message)
        
        no_errors = self.module_manager.post_install()
        if not no_errors:
            self.message_label.setText(self.post_error_messsage)
    
        
    def on_close(self):
        self.close()
        
    def clean(self):
        self.movie.stop()
        if self.device.isOpen():
            self.device.close()

    def closeEvent(self, event):
        self.clean()
        
        
        
class MyInstaller(ModuleManager):
    def __init__(self, *args, **kwargs):
        super(MyInstaller, self).__init__(*args, **kwargs)

        
    def get_remote_package(self):
        """returns the github or PyPi name needed for installing"""

        return r'https://github.com/Nathanieljla/wing-ide-maya/archive/refs/heads/main.zip'
              
        
    
def main():
    if MAYA_RUNNING:
        manager = MyInstaller('wing', 1.0, package_name = 'wing-ide-maya')
        
        Resources.company_base64 = r'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'
        logo_size = [64 / 64]
        background_color = ''

        global RESOURCES
        RESOURCES = Resources()
        window_name =  manager.module_name.replace("_", " ")
        installer = InstallerUi(window_name, manager, background_color=background_color, company_logo_size=logo_size) #, launch_message='Welcome!')
        RESOURCES.set_installer(installer)

        installer.show()

           
def onMayaDroppedPythonFile(*args):
    main()
    

def run():
    """
    Run is a function used by WingIDE to execute code after telling Maya to import the module
    """    
    main()
    

if __name__ == "__main__":
    main()