// Decompile every function in the program and write pseudo-C to <outdir>/decomp_<segment>.c
// Usage (headless): -postScript DecompileAll.java <outdir>
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import java.io.*;
import java.util.*;

public class DecompileAll extends GhidraScript {
    @Override
    public void run() throws Exception {
        String outDir = getScriptArgs().length > 0 ? getScriptArgs()[0] : "decomp";
        new File(outDir).mkdirs();
        DecompInterface di = new DecompInterface();
        DecompileOptions opts = new DecompileOptions();
        di.setOptions(opts);
        di.openProgram(currentProgram);
        Map<String, PrintWriter> files = new TreeMap<>();
        PrintWriter index = new PrintWriter(new FileWriter(outDir + "/functions.tsv"));
        int n = 0, fail = 0;
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) {
            String addr = f.getEntryPoint().toString();
            String seg = addr.contains(":") ? addr.substring(0, addr.indexOf(':')) : "flat";
            PrintWriter pw = files.computeIfAbsent(seg, s -> {
                try { return new PrintWriter(new FileWriter(outDir + "/decomp_" + s + ".c")); }
                catch (IOException e) { throw new RuntimeException(e); }
            });
            DecompileResults r = di.decompileFunction(f, 60, monitor);
            index.println(addr + "\t" + f.getName() + "\t" + f.getBody().getNumAddresses());
            pw.println("// ==== " + addr + " " + f.getName());
            if (r != null && r.decompileCompleted()) {
                pw.println(r.getDecompiledFunction().getC());
            } else {
                pw.println("// decompile failed: " + (r == null ? "null" : r.getErrorMessage()));
                fail++;
            }
            n++;
        }
        for (PrintWriter pw : files.values()) pw.close();
        index.close();
        println("Decompiled " + n + " functions, " + fail + " failures");
    }
}
