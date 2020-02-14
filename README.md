# OpenSCAD-Parallel-Build

This is a small python tool simplifying the work with OpenSCAD. It allows you to parallelize the build of multiple parts and simplifies handling multiple parts in a single file.

## Requirements
You just need to have Python 3 and (of course) OpenSCAD installed.

## Limitations
At the moment, it works only on macOS. But it should work at least on Linux if you add the path to the OpenSCAD binary.

## How does it work?
```
./openscad-parallel-build.py /path/to/your/openscad/files /path/to/put/stl/files
```
This will compile all `.scad` files in `/path/to/your/openscad/files` and create a new folder `out` in `/path/to/put/stl/files` where all STL files will be put in.
It starts as many OpenSCAD processes as your CPU has cores, so the compilation process will be significantly faster.

## How to use extended features?
You can add properties to your `.scad` files which will be used by OpenSCAD-Parallel-Build to customise the build process. Add the following block to your code:
```openscad
//PARALLEL-PROPS
...your properties here...
//END-PARALLEL-PROPS
```

### Testing mode
In some cases, you have objects in your file to simplify the design process that shouldn't be exported to STL. So, you simpy add
```openscad
TEST_MODE = 1;
```
to your properties. Now, put any code which shoudn't be exported into an if expression:
```openscad
if (TEST_MODE == 1) {
    helper_model();
}
model_to_print();
```
The export runs with `TEST_MODE = 0` so yout helpers don't get exported.

### Different resolution
To get better preview performance you might have reduced the `$fn` variable. But in the exported model, you want a better resolution. OpenSCAD-Parallel-Build will overwrite the resolution on compiling. Add:
```openscad
RENDER_WITH = 100; // Set it to the resolution you want
```
to your properties.

### Export multiple models from a single file
Sometimes, when you design a more complex model, you realize that it's better to print it in multiple parts. OpenSCAD-Parallel-Build has everything you need to simplify thid process. Add this to your properties:
```openscad
AVAILABLE_MODES = 2; // Set it to the number of models you have
```
On compilation, OpenSCAD-Parallel-Build will add a variable `EXPORT_MODE = 0` counting up from `0` to `AVAILABLE_MODES - 1`. So, you have to put your models into if expressions:
```openscad
if (EXPORT_MODE == 0 || TEST_MODE == 1) {
    first_model_to_print();
}
if (EXPORT_MODE == 1 || TEST_MODE == 1) {
    second_model_to_print();
}
```
This example will create the STL files `INPUTFILENAME_0.stl` and `INPUTFILENAME_1.stl`.
