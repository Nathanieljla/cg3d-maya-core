
import re


def remove_namespaces(filename):
    """FBX must be saved in ACSII format otherwise the parser will error."""
    
    fbx = open(filename)
    file_string = fbx.read()
    fbx.close()
    
    results = re.finditer('(Model::[_:a-z0-9]*)', file_string, re.IGNORECASE)
    segments = []
    for i in results:
        start_end = ([i.start(), i.end()])
        segments.append(start_end)
        
    segments.reverse()
    for idx, i in enumerate(segments):
        model_name = file_string[i[0]:i[1]]
        model_name = model_name.replace('Model::', '')
        namespaces = model_name.split(':')
        model_name = 'Model::{0}'.format(namespaces[-1])
        
        pre_file  = file_string[0:i[0]]
        post_file = file_string[i[1]:]

        file_string = pre_file + model_name + post_file
        
    new_file = open(filename, 'w')
    new_file.write(file_string)
    new_file.close()
