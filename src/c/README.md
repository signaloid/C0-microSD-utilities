# Signaloid C0 compute-module C library

C sources, headers and build glue for applications that run on the Signaloid
C0 compute modules. The library is organised so that a single application
source tree can target any compute-module variant unchanged — the
variant-specific details live behind a Hardware Abstraction Layer (HAL).

## Directory layout

```
src/c/
  include/
    C0HAL.h .................... public HAL entry point; include this from app code.
                                 Declares the variant-agnostic HAL API and shared
                                 output/input buffer accessors, and dispatches to the
                                 active variant's HAL header based on BUILD_FOR.
    C0mmioCommonHAL.h .......... shared MMIO memory model (single buffer split into
                                 output/input windows) reused by several variants.
    C0SoCStatus.h .............. common host/device status-register values.
    C0Logger.h ................. logging helper built on top of the HAL.
    SignaloidBuildTargets.h .... BUILD_FOR target identifiers.
    C0<variant>/ ............... one folder per compute-module variant:
      Constants.h .............. register/buffer offsets (often sourced from the
                                 variant's regmap under ../regmaps/C0<variant>/).
      HAL.h .................... variant register layout, config-register union,
                                 register-access macros and buffer sizing.
      HostUtils.h .............. host-side helpers for talking to the variant.
  src/
    C0Logger.c ................. logger implementation (variant-agnostic).
    C0<variant>/HAL.c .......... variant HAL implementation (device/SoC side). Each
                                 file is guarded so it compiles to an empty
                                 translation unit unless it matches BUILD_FOR.
  lib/
    C0<variant>/HostUtils.c .... host-side helper implementation.
  regmaps/
    C0<variant>/ ............... auto-generated register maps for the variant.
  common/ ...................... per-variant startup (init-pro.S, startup.cpp) and
                                 linker scripts.
  Makefile ..................... selects the variant via DEVICE_TYPE and compiles the
                                 matching HAL source through HAL_SRC.
```

## How the HAL selects a variant

Application code includes only `C0HAL.h`. The build defines `BUILD_FOR` (from
`DEVICE_TYPE` in the `Makefile`) to one of the identifiers in
`SignaloidBuildTargets.h`. `C0HAL.h` then includes the matching
`C0<variant>/HAL.h`, and the `Makefile` compiles the matching
`src/C0<variant>/HAL.c`.

Everything for one variant is therefore self-contained under its `C0<variant>/`
folders (`include/`, `src/`, `lib/`, `regmaps/`).

