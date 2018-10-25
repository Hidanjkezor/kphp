#!/usr/bin/python3

import json
import shutil
import sys
import jsonschema
from pathlib import Path

REL_DIR = Path('auto') / 'PHP' / 'compiler' / 'vertex'
DIR = Path(__file__).resolve().parents[2] / REL_DIR


def clear_dir():
    if DIR.exists():
        shutil.rmtree(str(DIR))
    DIR.mkdir()


def open_file(name, once=True):
    f = (DIR / name).open('w')
    f.write("/* THIS FILE IS GENERATED. DON'T EDIT IT. EDIT vertex-desc.json.*/\n")
    if once:
        f.write("#pragma once\n")
    return f


def get_schema_properties(schema):
    return schema["definitions"]["operation_property_dict"]["properties"]


def output_one_enum(f, name, values):
    f.write("enum {name} {{\n".format(name=name))

    for val in values:
        f.write("  " + val + ",\n")

    f.write("};\n")


def output_enums(data, schema):
    with open_file("vertex-types.h") as f:
        output_one_enum(f, "Operation", [i["name"] for i in data] + ["Operation_size"])

        props = get_schema_properties(schema)
        for i in props:
            if "enum" in props[i]:
                f.write("\n")
                name = "opp_%s_t" % i
                if "title" in props[i]:
                    name = props[i]["title"]
                output_one_enum(f, name, props[i]["enum"])


def output_include_directive(f, name):
    if name == "meta_op_base":
        f.write('#include "compiler/vertex-meta_op_base.h"\n')
    else:
        f.write('#include "%s/vertex-%s.h"\n' % (REL_DIR, name))


def output_class_header(f, base_name, name):
    f.write("""
template<> 
class vertex_inner<{name}> : public vertex_inner<{base_name}> {{
public:""".format(name=name, base_name=base_name))


def get_string_extra():
    return """
  virtual const string &get_string() const override { return str_val; }
  virtual void set_string(const string &s) override { str_val = s; }
  virtual bool has_get_string() const override { return true; }
"""


def get_function_extra():
    return """
  virtual const FunctionPtr &get_func_id() const override { return func_; }
  virtual void set_func_id(FunctionPtr func_ptr) override { func_ = func_ptr; }
"""


def get_variable_extra():
    return """
  virtual const VarPtr &get_var_id() const override { return var_; }
  virtual void set_var_id(const VarPtr &var) override { var_ = var; }
"""


def output_extras(f, type_data):
    if "extras" in type_data:
        type_data.setdefault("extra_fields", {})

        do_with_extras = {
            "string": ("str_val", "std::string", get_string_extra),
            "function": ("func_", "FunctionPtr", get_function_extra),
            "variable": ("var_", "VarPtr", get_variable_extra)
        }

        for extra_name in type_data["extras"]:
            assert extra_name in do_with_extras
            (var_name, type, fun_get_extra) = do_with_extras[extra_name]

            type_data["extra_fields"][var_name] = {'type': type}
            f.write(fun_get_extra())


def output_one_extra_field(f, name, desc):
    f.write('  ' + desc["type"] + ' ' + name)
    if "default" in desc:
        f.write(" = " + str(desc["default"]))
    f.write(";\n")


def output_extra_fields(f, type_data):
    if "extra_fields" in type_data:
        f.write("private:\n")
        extra_fields = type_data["extra_fields"]
        for extra_field in extra_fields:
            if extra_field[-1] == '_':
                output_one_extra_field(f, extra_field, extra_fields[extra_field])

        f.write("public:\n")
        for extra_field in extra_fields:
            if extra_field[-1:] != '_':
                output_one_extra_field(f, extra_field, extra_fields[extra_field])


def output_create_function(f, name):
    f.write("""
  template<typename... Args> 
  static vertex_inner<{name}> *create(Args&&... args) {{ 
    auto v = raw_create_vertex_inner<{name}>(get_children_size(std::forward<Args>(args)...)); 
    v->set_children(0, std::forward<Args>(args)...); 
    return v; 
  }} 
""".format(name=name))


def output_props_dictionary(f, schema, props, cnt_spaces):
    for prop_name in props:
        prop_value = props[prop_name]
        if get_schema_properties(schema)[prop_name].get("type", "") == "string":
            prop_value = '"' + prop_value + '"'

        spaces = cnt_spaces * " "
        f.write(spaces)
        f.write("p->{prop_name} = {prop_value};\n".format(prop_name=prop_name, prop_value=prop_value))


def output_props(f, type_data, schema):
    if "props" in type_data:
        f.write("  static void init_properties(OpProperties *p) {\n")
        f.write("    vertex_inner<{name}>::init_properties(p);\n".format(name=type_data["base_name"]))

        output_props_dictionary(f, schema, type_data["props"], 4)

        if "safe_props" in type_data:
            f.write("    if (use_safe_integer_arithmetic) {\n")
            output_props_dictionary(f, schema, type_data["safe_props"], 6)

            f.write("    }\n")
        f.write("  }\n")


def output_sons(f, type_data):
    if "sons" in type_data:
        f.write("\n")
        for son_name in type_data["sons"]:
            son_properties = type_data["sons"][son_name]
            if isinstance(son_properties, int):
                son_properties = {"id": son_properties}

            son_id = son_properties["id"] if "id" in son_properties else son_properties
            optional = "optional" in son_properties
            virtual = "virtual" if "virtual" in son_properties else ""
            override = "override" if "override" in son_properties else ""

            if son_id < 0:
                son_id = "size() - " + str(-son_id)
            else:
                son_id = str(son_id)

            if optional:
                f.write("  {virtual} bool has_{son_name}() const {override} {{ return check_range({son_id}); }}\n"
                        .format(virtual=virtual, son_name=son_name, son_id=son_id, override=override))

            f.write("  {virtual} VertexPtr &{son_name}() {override} {{ return ith({son_id}); }}\n"
                    .format(virtual=virtual, son_name=son_name, son_id=son_id, override=override))

            f.write("  {virtual} const VertexPtr &{son_name}() const {override} {{ return ith({son_id}); }}\n"
                    .format(virtual=virtual, son_name=son_name, son_id=son_id, override=override))


def output_aliases(f, type_data):
    if "alias" in type_data:
        f.write("\n")
        for i in type_data["alias"]:
            f.write("  VertexPtr &%s() { return %s(); }\n" % (i, type_data["alias"][i]))
            f.write("  const VertexPtr &%s() const { return %s(); }\n" % (i, type_data["alias"][i]))


def output_ranges(f, type_data):
    def convert_range(value, zero):
        if value > 0:
            return "begin() + %d" % value
        elif value < 0:
            return "end() - %d" % (-value)

        return zero

    if "ranges" in type_data:
        f.write("\n")
        for range_name in type_data["ranges"]:
            from_r = convert_range(type_data["ranges"][range_name][0], "begin()")
            to_r = convert_range(type_data["ranges"][range_name][1], "end()")

            f.write("  VertexRange %s() { return VertexRange(%s, %s); }\n" % (range_name, from_r, to_r))
            f.write("  VertexConstRange %s() const { return VertexConstRange(%s, %s); }\n" % (range_name, from_r, to_r))


def output_class_footer(f):
    f.write("};\n")


def output_vertex_type(type_data, schema):
    if "base_name" not in type_data: return

    (name, base_name) = (type_data["name"], type_data["base_name"])

    with open_file("vertex-" + name + '.h') as f:
        output_include_directive(f, base_name)
        output_class_header(f, base_name, name)

        output_extras(f, type_data)
        output_extra_fields(f, type_data)

        output_create_function(f, name)
        output_props(f, type_data, schema)

        output_sons(f, type_data)
        output_aliases(f, type_data)
        output_ranges(f, type_data)

        output_class_footer(f)


def output_all(data):
    with open_file("vertex-all.h") as f:
        for vertex in data:
            output_include_directive(f, vertex["name"])


def output_foreach_op(data):
    with open_file("foreach-op.h", once=False) as f:
        for vertex in data:
            if vertex["name"] != "op_err":
                f.write('FOREACH_OP(%s)\n' % vertex["name"])

        f.write("#undef FOREACH_OP\n")


if __name__ == "__main__":
    print(DIR)
    with open(sys.argv[1]) as f:
        data = json.load(f)

    with open(sys.argv[1].replace(".json", ".config.json")) as f:
        schema = json.load(f)

    jsonschema.validators.Draft4Validator.check_schema(schema)
    jsonschema.validate(data, schema)

    clear_dir()
    output_enums(data, schema)

    for vertex in data:
        output_vertex_type(vertex, schema)

    output_all(data)
    output_foreach_op(data)