#!/usr/bin/env python

# Converts patterns from the C source code arrays to Python code

# !wget https://raw.githubusercontent.com/pichenettes/eurorack/master/grids/resources.cc
# ./convert_resources_cc.py

import re


def convert_cpp_arrays_to_python(cpp_file_path, python_file_path):
    with open(cpp_file_path, "r") as cpp_file:
        content = cpp_file.read()

    # Regular expression to match C++ array declarations
    pattern = r"const\s+prog_uint8_t\s+(\w+)\[\]\s+PROGMEM\s*=\s*\{([^}]+)\};"

    with open(python_file_path, "w") as python_file:
        python_file.write("from array import array\n\n")

        for match in re.finditer(pattern, content):
            array_name = match.group(1)
            array_values = match.group(2)

            # Convert values to a list of integers
            values = [int(x.strip()) for x in array_values.split(",") if x.strip()]

            # Create the Python array string with 32 values per line
            python_file.write(f"{array_name} = array('B', [\n")
            for i in range(0, len(values), 32):
                line = "    " + ", ".join(map(str, values[i : i + 32]))
                python_file.write(line)
                if i + 32 < len(values):
                    python_file.write(",\n")
                else:
                    python_file.write("\n")
            python_file.write("])\n\n")


if __name__ == "__main__":
    cpp_file_path = "resources.cc"
    python_file_path = "resources_cc.py"
    convert_cpp_arrays_to_python(cpp_file_path, python_file_path)
