// Pre-analysis: set DS = DGROUP (arg, hex paragraph, already including the loader's base) over all memory.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.lang.Register;
import ghidra.program.model.mem.MemoryBlock;
import java.math.BigInteger;

public class SetDS extends GhidraScript {
    @Override
    public void run() throws Exception {
        long ds = Long.parseLong(getScriptArgs()[0], 16);
        Register r = currentProgram.getRegister("ds");
        for (MemoryBlock b : currentProgram.getMemory().getBlocks()) {
            if (!b.isInitialized()) continue;
            currentProgram.getProgramContext().setValue(r, b.getStart(), b.getEnd(), BigInteger.valueOf(ds));
        }
        println("DS set to " + Long.toHexString(ds));
    }
}
