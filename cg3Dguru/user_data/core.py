import pymel.core as pm
#import exceptions

"""
#don't change unless your project really desires an alternative name
#for the life of all scripts and tools that leverage the user_data module.
#you must change whenever getting an updated version of the module.
"""
_RECORDS_NAME      = 'DataRecords'
_DEFAULT_NODE_TYPE = 'network'

AUTO_UPDATE = True


class VersionUpdateException(Exception):
    pass


class Attr(object):
    def __init__(self, name, attr_type, *args, **kwargs):
        self.name = name
        self.attrType = attr_type
        self.args = args
        self._flags = kwargs
        self._clear_invalid_flags(self._flags)



    def _clear_invalid_flags(self, flags):
        invalid = [ 'longName', 'ln', 'attribute', 'at', 'dataType', 'dt', 'p', 'parent', 'numberOfchildren', 'nc']
        for key in invalid:
            if key in flags:
                flags.pop(key)
        
        
        
        
class Compound(Attr):
    compound_types = {'compound':0,
                     'reflectance':3, 'spectrum':3,
                     'float2':2, 'float3':3,
                     'double2':2, 'double3':3,
                     'long2':2, 'long3':3,
                     'short2':2, 'short3':3
                    }
    
    def __init__(self, name, attr_type, children = [], make_elements = True, *args, **kwargs):
        super(Compound, self).__init__(name, attr_type, *args, **kwargs)
        
        if attr_type not in Compound.compound_types:
            pm.error('UserData Module: {0} is not a valid CompoundType.  Print Compound.CompoundTypes for valid list'.format(attr_type))
        
        self._target_size = Compound.compound_types[attr_type]
        self._children   = children
        
        if self._target_size and make_elements:
            if self._children:
                pm.error('UserData Module: {0} can\t use _MakeElements with Compound class, if you also supply children')
            
            self._make_elements()


            
    def _make_elements(self):
        #define suffix for children
        xyz = ['X', 'Y', 'Z']
        rgb = ['R', 'G', 'B']
        
        suffix = xyz
        if 'usedAsColor' in self._flags or 'uac' in self._flags or \
           self.attrType == 'spectrum' or self.attrType == 'reflectance':
            suffix = rgb
            
        #determine child type            
        type = 'double'
        if self.attrType[0] == 'f':
            type = 'float'
        elif self.attrType[0] == 'l':
            type = 'long'
        elif self.attrType[0] == 's':
            type = 'short'
            
        #add children to compound
        for i in range(0, self._target_size):
            attr = Attr(self.name + suffix[i], type)
            self.add_child(attr)
        
        
    def count(self):
        return len(self._children)
    
    
    def add_child(self, child):
        if self._target_size and len(self._children) > self._target_size:
            pm.error('UserData Module: Compound instance has reach max allowed children')
            
        self._children.append(child)
        
        
    def get_children(self):
        return self._children
        
        
    def validate(self):
        valid_size = False
        if not self._target_size:
            valid_size = len(self._children) > 0
        else:
            valid_size = self.count() == self._target_size
            
        if not valid_size:
            pm.error('UserData Module: {0} does not have the required number of children'.format(self.attrType))



class Record(object):
    def __init__(self, attr):
        self._attr = attr
        self._name, str_version = attr.get().split(':')
        self._version = tuple(map(int, str_version.split('.')))
        

    @property
    def name(self):
        return self._name

        
    @property
    def version(self):
        return self._version
    
    
    @version.setter
    def version(self, value):
        self.attr.unlock()
        self._version = value
        name = '{0}:{1}'.format( self.name, self.get_version_string() )
        self.attr.set( name )
        self.attr.lock()  
        
        
    @property
    def attr(self):
        return self._attr
    
    
    def get_version_string(self):
        return '.'.join(map(str, self._version))
    
    
    
class BaseData(object):
    attributes       = []
    data_types = set(['string', 'stringArray', 'matrix', 'fltMatrix', 'reflectanceRGB', 'spectrumRGB',
                     'float2', 'float3', 'double2', 'double3', 'long2', 'long3', 'short2', 'short3'                     
                    'doubleArray', 'floatArray', 'Int32Array', 'vectorArray', 'nurbsCurve', 'nurbsSurface',
                    'mesh', 'lattice', 'pointArray'])
    _version = (0, 0, 0)

    def __init__(self, version = (0, 0, 0), *args, **kwargs):  
        super(BaseData,self).__init__(*args, **kwargs)
        self.version = version
        
        flags = self.get_default_flags()
        flags.update( kwargs )
        self._clear_invalid_flags( flags )
        
        self._flags   = flags
        self._records = None
        self._node    = None
        
        self._init_class_attributes()


###----Versioning Methods----


    @classmethod
    def get_class_version(cls):
        return cls._version
    

    @classmethod
    def set_class_version(cls, version):
        cls._version = version
        
    @classmethod
    def get_version_string(cls):
        return '.'.join(map(str, cls.version))

    
    @property
    def version(self):
        return self.get_class_version()
        
        
    @version.setter
    def version(self, value):
        self.set_class_version(value)
        
        
        
###---Flag Methods----
        
        
    @staticmethod
    def _clear_invalid_flags(flags):
        invalid = [ 'longName', 'ln', 'attribute', 'at', 'dataType', 'dt', 'p', 'parent', 'numberOfchildren', 'nc']
        for key in invalid:
            if key in flags:
                flags.pop(key)    

        
        
    @classmethod
    def get_default_flags(cls):
        return {}
        
        
###----Record Methods-----

        
    def _add_data_to_records(self):
        if self._records:

            indices = self._records.getArrayIndices()
            if not indices:
                idx = 0
            else:
                idx = -1
                for i in range(0, indices[-1]):
                    if not i in indices:
                        idx = i
                        break
                    
                if idx == -1:
                    idx = indices[-1] + 1
            
            #concatenating the name and version is not as clean in code
            #(vs seperate attributes), but it makes end-user view from
            #the attribute editor clean while not taking up much UI space
            name = '{0}:{1}'.format( self.get_data_name(), self.get_version_string() )
            self._records[idx].set( name )
            self._records[idx].lock()
            
            #self._records[idx].dataName.set( self.GetDataName() )
            #self._records[idx].version.set( self.Version )
            #self._records[idx].lock()
            
                  
            
    @staticmethod
    def _create_records(node):
        global _RECORDS_NAME
        pm.addAttr(node, ln = _RECORDS_NAME,  dt = 'string', m= True)
          
        #pm.addAttr(node, ln = _RECORDS_NAME, at = 'compound', nc = 1)  
        #pm.addAttr(node, ln = 'records',   at = 'compound', nc = 2, m= True, parent = _RECORDS_NAME)
        #pm.addAttr(node, ln = 'dataName',  dt = 'string', parent = 'records')
        #pm.addAttr(node, ln = 'version',   at = 'long',   parent = 'records')        
                        
           
    @classmethod     
    def _get_records(cls, node, force_add ):
        if not node:
            pm.error('UserData Module : Can\'t get records. node is None')
            
        has_records = pm.hasAttr(node, _RECORDS_NAME)
                
        if (not has_records) and force_add:
            cls._create_records( node )
            has_records = True
        
        if has_records:
            return node.attr(_RECORDS_NAME) #.records
        else:
            return None
        
        
 
    @classmethod
    def get_records(cls, node):
        return cls._get_records(node, False)
 
        

    @classmethod
    def _get_record_by_name(cls, node, data_name):
        records = cls._get_records(node, False)
        found_record = None
        if records:
            for i in records.getArrayIndices():
                record = records[i]
                if not record.get():
                    continue
                
                name, version = record.get().split(':')
                if name == data_name:
                    found_record = Record(record)
                    break
                
        return found_record           

    
    
    @classmethod
    def get_record_by_name(cls, node, data_name):
        return cls._get_record_by_name( node, data_name )
    
    
    
    @classmethod
    def get_record(cls, node):
        return cls._get_record_by_name( node, cls.get_data_name() )
              
              
              
###----Attribute Methods----
 
    def _find_attr_conflicts(self):
        attr_names = self.get_attribute_names()  
        if 'multi' in self._flags or 'm' in self._flags:
            #I *believe* attributes that are part of a multi arg won't conflict.            
            attr_names = []       
        
        attr_names.append( self.get_data_name() )
        
        conflicts = []
        for attr_name in attr_names:
            if pm.hasAttr(self._node, attr_name):
                conflicts.append(attr_name)
                
        if conflicts:
            record_names = []
            for i in self._records.getArrayIndices():
                record = Record(self._records[i])
                record_names.append( record.name )            

            class_name = self.__class__.__name__
            errorMessage = 'UserData Attribute Conflict :: Attribute Name(s) : {0} from class "{1}" conflicts with one of these existing blocks of data : {2}'
            pm.error( errorMessage.format(conflicts, class_name, record_names) )
 
               
    def add_attr(self, attr, parent_name):
        if parent_name:
            attr._flags['parent'] = parent_name
           
        if isinstance(attr, Compound):
            attr.validate()
            pm.addAttr(self._node, ln = attr.name, at = attr.attrType, nc = attr.count(), **attr._flags)
            for child in attr.get_children():
                self.add_attr(child, attr.name)
            
        elif attr.attrType in self.__class__.data_types:
            pm.addAttr(self._node, ln = attr.name, dt = attr.attrType, **attr._flags)             
        else:   
            pm.addAttr(self._node, ln = attr.name, at = attr.attrType, **attr._flags)     
           
           
    @classmethod                   
    def _get_attribute_names(cls, attr, name_list):
        name_list.append(attr.name)
        if isinstance(attr, Compound):
            for child in attr.get_children():
                cls._get_attribute_names(child, name_list)
            
            
    @classmethod        
    def get_attribute_names(cls):
        """
        returns a flat list of all the attribute names of the class.attributes.
        """
        name_list = []
        cls._init_class_attributes()
            
        for attr in cls.attributes:
            cls._get_attribute_names(attr, name_list)
            
        return name_list

      
    @classmethod
    def _init_class_attributes(cls):
        if not cls.attributes:
            cls.attributes = cls._get_attributes()
        
        
        
    @classmethod
    def _get_attributes(cls):
        pm.error( 'UserData Module: You\'re attempting to get attributes for class {0} that has no GetAttributes() overridden'.format(cls.__name__) )       
       
       
       
###----Update Methods----

    def pre_update_version(self, old_data, old_version_number):
        """
        Overwrite : 
        """
        global AUTO_UPDATE
        return AUTO_UPDATE
     
      
    def update_version(self, old_data, old_version_number):
        #Copy the attribute values to a temporary node
        temp_node, data = self.create_node(name = 'TRASH', ss=True)
        name_list = self.get_attribute_names()
        try:
            pm.copyAttr(self._node, temp_node, at = name_list, ic = True, oc = True, values = True)
        except:
            #delete the tempNode
            pm.delete(temp_node)
            
            message = 'Please impliment custom update logic for class: {0}  oldVersion: {1}  newVersion: {2}'.format( self.get_data_name(), old_version_number, self.version)
            raise VersionUpdateException(message)
        
        #delete the attributes off the current node
        pm.deleteAttr( self._node, at = self.get_data_name() )
        
        #rebuild with the latest definition
        self._create_data()

        #transfer attributes back to original node
        pm.copyAttr(temp_node, self._node, at = name_list, ic = True, oc = True, values = True)  
        
        #delete the tempNode
        pm.delete(temp_node)
        
        return True

        
     
    def post_update_version(self, data, update_successful):
        """
        Overwrite : 
        """        
        pass
    
    
###----Data Methods----
    
    @classmethod
    def get_data_name(cls):
        """
        Overwrite : 
        """
        return cls.__name__
            
            
    
    def _create_data(self):     
        attrs = self.__class__.attributes
        long_name = self.get_data_name()
        pm.addAttr(self._node, ln = long_name, at = 'compound', nc = len( attrs ), **self._flags )

        for attr in attrs:
            self.add_attr(attr, long_name)       
         
        return self._node.attr(long_name)
        
        
           
    def post_create(self, data):
        """
        Overwrite : 
        """        
        pass
              
              
    
    def get_data(self, node, force_add = False):
        #should be cleared, but let's be sure.
        self._records = None
        self._node    = node
        
        record = self.get_record(node)
        
        if not record and force_add:
            #lets make sure the records data exists
            self._records = self._get_records(node, force_add = True)
            
        #If found make sure the data block doesn't need updating.
        if record:
            data_name = self.get_data_name() 
            record_version = record.version #.get()
            current_version = self.version
            
            #Attempt to updat the version
            if record_version < current_version:
                old_data = self._node.attr(data_name)
                
                if self.pre_update_version(old_data, record_version):
                    updated = self.update_version(old_data, record_version)
                    if updated:
                        record.version = current_version
                                
                    data = self._node.attr(data_name)
                    self.post_update_version( data, updated )

            
            data = self._node.attr(data_name)
                    
                    
        #else, add the data to the node           
        elif force_add:
            self._find_attr_conflicts()
            data = self._create_data()
            self._add_data_to_records()
            self.post_create( data )
            
        else:
            data = None
            
        self._records = None        
        self._node    = None
        return data      
    
    
        
    def add_data(self, node):
        return self.get_data(node, force_add=True)


    def delete_data(self, node):   
        record = self.get_record(node)
        
        if record:
            record.attr.unlock()
            pm.removeMultiInstance(record.attr, b=True)
            pm.deleteAttr(node, at = self.get_data_name() )   
            

###----Misc Methods----
    
    @classmethod
    def create_node(cls, nodeType = _DEFAULT_NODE_TYPE, *args, **kwargs):
        pynode = pm.general.createNode(nodeType, **kwargs)
    
        if pynode:
            classInstance = cls()
            data = classInstance.get_data(pynode, force_add = True)
            
        return (pynode, data)   
    
    
    
    
    
    
class Utils(object):
    def __init__(self, *args, **kwargs):
        super(Utils, self).__init__(*args, **kwargs)
    
    
    @staticmethod
    def get_classes():
        classes = BaseData.__subclasses__()
        return classes
    
    
    @staticmethod
    def get_class_names():
        sub_classes = Utils.get_classes()
        class_names = {}
        for subclass in sub_classes:
            class_names[ subclass.get_data_name() ] = subclass
            
        return class_names

    
    @staticmethod
    def find_attribute_conflicts(error_on_conflict = True):
        conflicts = {}
        attrs = {}
        for subclass in Utils.get_classes():
            default_flags = subclass.GetDefaultFlags()
            
            #if the Class is going to be added with a mutli flag, then there
            #there shouldn't be any conflicts with its attributes
            if 'm' in default_flags or 'multi' in default_flags:
                continue
            
            attribute_names = subclass.GetAttributeNames()
            for attr_name in attribute_names:
                if attr_name not in attrs:
                    attrs[attr_name] = [subclass.__name__]
                else:
                    attrs[attr_name].append(subclass.__name__)
                    
        for attr_name in attrs:
            classes = attrs[attr_name]
            
            if len(classes) > 1:
                conflicts[attr_name] = classes
                
        if conflicts:
            for attr_name in conflicts:
                classes = conflicts[attr_name]
                pm.warning( 'UserData.Utils :: Attr conflict. : "{0}" exists in classes: {1}'.format(attr_name, classes))
                
            if error_on_conflict:
                pm.error( 'UserData.Utils :: Found conflict between attribute names. See console for info.')
                
        return conflicts
    
    
    @staticmethod
    def get_nodes_with_data(data_class = None, *args, **kwargs):
        nodes = pm.ls(*args, **kwargs)
        nodes.sort()
        
        data_nodes = []
        for node in nodes:
            if data_class:
                records = BaseData.get_record_by_name( node, data_class.get_data_name() )
            else:
                records = BaseData.get_records(node)
                
            if records:
                data_nodes.append(node)
                
        return data_nodes
    
    
    @staticmethod
    def validate_version(*args, **kwargs):
        nodes = pm.ls(*args, **kwargs)
        
        classes= Utils.get_classes()
        
        for data_class in classes:
            instance = data_class()
            
            for node in nodes:
                #this forces a version check
                instance.get_data(node)

        
            
    
    

