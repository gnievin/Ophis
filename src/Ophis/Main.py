"""Main controller routines for the Ophis assembler.

    When invoked as main, interprets its command line and goes from there.
    Otherwise, use run_ophis(cmdline-list) to use it inside a script."""

# Copyright 2002-2012 Michael C. Martin and additional contributors.
# You may use, modify, and distribute this file under the MIT
# license: See README for details.

import sys
import Ophis.Frontend
import Ophis.IR
import Ophis.CorePragmas
import Ophis.Passes
import Ophis.Errors as Err
import Ophis.Environment
import Ophis.CmdLine
import Ophis.Opcodes


def run_all(infiles, outfile):
    "Transforms the source infiles to a binary outfile."
    Err.count = 0
    z = Ophis.Frontend.parse(infiles)
    env = Ophis.Environment.Environment()

    m = Ophis.Passes.ExpandMacros()
    i = Ophis.Passes.InitLabels()
    l_basic = Ophis.Passes.UpdateLabels()
    l = Ophis.Passes.FixPoint("label update", [l_basic],
                              lambda: not l_basic.changed)
    c_basic = Ophis.Passes.Collapse()
    c = Ophis.Passes.FixPoint("instruction selection 1", [l, c_basic],
                              lambda: not c_basic.changed)
    b = Ophis.Passes.ExtendBranches()
    a = Ophis.Passes.Assembler()

    passes = []
    passes.append(Ophis.Passes.DefineMacros())
    passes.append(Ophis.Passes.FixPoint("macro expansion", [m],
                                        lambda: not m.changed))
    passes.append(Ophis.Passes.FixPoint("label initialization", [i],
                                        lambda: not i.changed))
    passes.extend([Ophis.Passes.CircularityCheck(),
                   Ophis.Passes.CheckExprs(),
                   Ophis.Passes.EasyModes()])
    passes.append(Ophis.Passes.FixPoint("instruction selection 2", [c, b],
                                        lambda: not b.changed))
    passes.extend([Ophis.Passes.NormalizeModes(),
                   Ophis.Passes.UpdateLabels(),
                   a])

    for p in passes:
        p.go(z, env)

    if Err.count == 0:
        try:
            if outfile == '-':
                output = sys.stdout
            elif outfile is None:
                output = file('ophis.bin', 'wb')
            else:
                output = file(outfile, 'wb')
            output.write("".join(map(chr, a.output)))
            output.flush()
            if outfile != '-':
                output.close()
        except IOError:
            print>>sys.stderr, "Could not write to " + outfile
    else:
        Err.report()


def run_ophis(args):
    Ophis.CmdLine.parse_args(args)
    Ophis.Frontend.pragma_modules.append(Ophis.CorePragmas)

    if Ophis.CmdLine.enable_undoc_ops:
        Ophis.Opcodes.opcodes.update(Ophis.Opcodes.undocops)
    elif Ophis.CmdLine.enable_65c02_exts:
        Ophis.Opcodes.opcodes.update(Ophis.Opcodes.c02extensions)

    Ophis.CorePragmas.reset()
    run_all(Ophis.CmdLine.infiles, Ophis.CmdLine.outfile)


if __name__ == '__main__':
    run_ophis(sys.argv[1:])
