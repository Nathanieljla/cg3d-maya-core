
import re


def remove_namespaces(filename, remove_subdeformer_namespaces=False):
    """FBX must be saved in ACSII format otherwise the parser will error."""
    
    fbx = open(filename)
    file_string = fbx.read()
    fbx.close()
    
    #don't use \s in this otherwise it will wrap past the return character and cause issues
    expression_str = "(?P<start>::)(?P<namespace>([ \d\w]*:)*)(?P<name>[ \d\w]*)"
    result = re.sub(expression_str, "\g<start>\g<name>", file_string)

    if remove_subdeformer_namespaces:
        expression_str = "(?P<start>SubDeformer::)(?P<namespace>([ \d\w]*\.)*)(?P<name>[ \d\w]*)"
        result = re.sub(expression_str, "\g<start>\g<name>", result)
        
    new_file = open(filename, 'w')
    new_file.write(result)
    new_file.close()


