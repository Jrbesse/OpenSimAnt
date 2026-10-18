using System.Reflection;
using System.Text;
using System.Text.Json;
using Formica.Sim;

namespace Formica.Replay;

/// <summary>Test player hooks matching the Python test suite's classes (by their recorded names).</summary>
public class TestSimPlayer : PlayerHooks
{
    public override void GameOver(State st) { }
    public override void WinScreen(State st) { }
    public override void ChoosePatch(State st) { }
}

public class FlowPlayer : TestSimPlayer
{
    public override int? NewGameDialog(State st) => 0;
}

public class QuietPlayer : NoPlayer
{
    public override void GameEvent(State st, int n) { }
}

public sealed class FuncStats
{
    public int Calls, Ok, Bad, Missing, Threw;
    public List<string> Notes = new();
}

/// <summary>Replays trace records on the C# port and compares return values and memory.</summary>
public sealed class Replayer
{
    static readonly Dictionary<string, string> ModuleClass = new()
    {
        ["rng"] = "Rng", ["state"] = "State", ["terrain"] = "Terrain", ["pheromones"] = "Pheromones",
        ["colony"] = "Colony", ["movement"] = "Movement", ["surface"] = "Surface", ["nestgrid"] = "NestGrid",
        ["nest"] = "Nest", ["red_nest"] = "RedNest", ["world"] = "World", ["yard"] = "Yard", ["sim"] = "Sim",
        ["newgame"] = "NewGame", ["game"] = "Game", ["savefile"] = "SaveFile", ["cheats"] = "Cheats",
        ["debug"] = "DebugCommands", ["tools"] = "MapTools", ["markers"] = "Markers", ["balloons"] = "Balloons",
        ["panels"] = "Panels", ["commands"] = "Commands", ["player"] = "Player",
    };

    static readonly Assembly SimAsm = typeof(State).Assembly;

    /// <summary>Reference names that differ from the C# ones (a method cannot share its class's name).</summary>
    static readonly Dictionary<string, string> Alias = new()
    {
        ["newgame.new_game"] = "NewGameStart",
        ["balloons.balloons"] = "Run",
    };

    public readonly Dictionary<string, FuncStats> Stats = new();
    public int MaxNotes = 4;
    public bool Verbose;

    public static IPlayer MakePlayer(string name) => name switch
    {
        null => new NoPlayer(),
        "simant_ref.surface.NoPlayer" => new NoPlayer(),
        "simant_ref.player.Hooks" => new PlayerHooks(),
        "test_sim.Player" => new TestSimPlayer(),
        "test_game.Flow" => new FlowPlayer(),
        "test_player.QuietPlayer" => new QuietPlayer(),
        _ => throw new NotSupportedException("player hooks " + name),
    };

    static readonly Dictionary<string, MethodInfo> MethodCache = new();

    public static MethodInfo FindMethod(string func, int nargs)
    {
        string key = func + "/" + nargs;
        if (MethodCache.TryGetValue(key, out var mi)) return mi;
        int dot = func.IndexOf('.');
        string mod = func[..dot], name = func[(dot + 1)..];
        if (Alias.TryGetValue(func, out var alias)) name = alias;
        mi = null;
        if (ModuleClass.TryGetValue(mod, out var cls))
        {
            var type = SimAsm.GetType("Formica.Sim." + cls);
            if (type != null)
            {
                string want = name.Replace("_", "");
                mi = type.GetMethods(BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static)
                    .Where(m => string.Equals(m.Name, want, StringComparison.OrdinalIgnoreCase))
                    .Where(m => m.GetParameters().Length >= nargs + 1
                                && m.GetParameters().Skip(nargs + 1).All(p => p.IsOptional))
                    .OrderBy(m => m.GetParameters().Length)
                    .FirstOrDefault();
            }
        }
        MethodCache[key] = mi;
        return mi;
    }

    static object ResolveRef(string name)
    {
        int dot = name.IndexOf('.');
        string mod = name[..dot], field = name[(dot + 1)..];
        var type = SimAsm.GetType("Formica.Sim." + ModuleClass[mod]) ?? throw new MissingMemberException(name);
        var f = type.GetField(field, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
        if (f != null) return f.GetValue(null);
        var p = type.GetProperty(field, BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
        if (p != null) return p.GetValue(null);
        throw new MissingMemberException(name);
    }

    public static object Convert(JsonElement e, Type t)
    {
        if (e.ValueKind == JsonValueKind.Object && e.TryGetProperty("$", out var tag))
        {
            if (tag.GetString() == "ref") return ResolveRef(e.GetProperty("name").GetString());
            if (tag.GetString() == "bytes" && t == typeof(byte[])) return System.Convert.FromHexString(e.GetProperty("hex").GetString());
            if (tag.GetString() == "callable" && typeof(Delegate).IsAssignableFrom(t))
            {
                // a Python test lambda for a screen-only callback: a no-op of the parameter's delegate type
                var inv = t.GetMethod("Invoke");
                var ps = inv.GetParameters().Select(p => System.Linq.Expressions.Expression.Parameter(p.ParameterType)).ToArray();
                System.Linq.Expressions.Expression body = inv.ReturnType == typeof(void)
                    ? System.Linq.Expressions.Expression.Empty()
                    : System.Linq.Expressions.Expression.Default(inv.ReturnType);
                return System.Linq.Expressions.Expression.Lambda(t, body, ps).Compile();
            }
            throw new NotSupportedException("argument " + e);
        }
        if (t == typeof(int)) return e.ValueKind switch
        {
            JsonValueKind.True => 1, JsonValueKind.False => 0, _ => (int)e.GetInt64(),
        };
        if (t == typeof(long)) return e.ValueKind switch
        {
            JsonValueKind.True => 1L, JsonValueKind.False => 0L, _ => e.GetInt64(),
        };
        if (t == typeof(bool)) return e.ValueKind switch
        {
            JsonValueKind.True => true, JsonValueKind.False => false, JsonValueKind.Null => false, _ => e.GetInt64() != 0,
        };
        if (t == typeof(string)) return e.ValueKind == JsonValueKind.Null ? null : e.GetString();
        if (t == typeof(int?)) return e.ValueKind == JsonValueKind.Null ? null : (int?)(int)e.GetInt64();
        if (t == typeof(int[])) return e.EnumerateArray().Select(x => (int)x.GetInt64()).ToArray();
        if (t.IsGenericType && t.FullName.StartsWith("System.ValueTuple"))
        {
            var ts = t.GetGenericArguments();
            var items = e.EnumerateArray().ToArray();
            var vals = ts.Select((tt, i) => Convert(items[i], tt)).ToArray();
            return Activator.CreateInstance(t, vals);
        }
        if (t == typeof(object)) return Raw(e);
        throw new NotSupportedException($"convert {e} to {t}");
    }

    static object Raw(JsonElement e) => e.ValueKind switch
    {
        JsonValueKind.Null => null,
        JsonValueKind.True => 1L,
        JsonValueKind.False => 0L,
        JsonValueKind.Number => e.GetInt64(),
        JsonValueKind.String => e.GetString(),
        JsonValueKind.Array => e.EnumerateArray().Select(Raw).ToList(),
        JsonValueKind.Object when e.TryGetProperty("$", out var tag) && tag.GetString() == "bytes" =>
            System.Convert.FromHexString(e.GetProperty("hex").GetString()).Select(b => (object)(long)b).ToList(),
        _ => e.ToString(),
    };

    /// <summary>Normalise a return value for comparison: bools as 0/1, ints as long, tuples as lists.</summary>
    public static object Norm(object v)
    {
        switch (v)
        {
            case null: return null;
            case bool b: return b ? 1L : 0L;
            case int i: return (long)i;
            case byte by: return (long)by;
            case long l: return l;
            case string s: return s;
            case System.Runtime.CompilerServices.ITuple tu:
                return Enumerable.Range(0, tu.Length).Select(k => Norm(tu[k])).ToList();
            case System.Collections.IEnumerable en: return en.Cast<object>().Select(Norm).ToList();
            default: return v.ToString();
        }
    }

    static bool Same(object a, object b)
    {
        if (a is List<object> la && b is List<object> lb)
            return la.Count == lb.Count && la.Zip(lb).All(p => Same(p.First, p.Second));
        return Equals(a, b);
    }

    static string Show(object v) => v switch
    {
        null => "None",
        List<object> l => "(" + string.Join(", ", l.Select(Show)) + ")",
        long x => $"{x} ({x:x})",
        _ => v.ToString(),
    };

    public static string Describe(int i)
    {
        int lin = State.Lo + i;
        foreach (var (seg, name) in new[] { (Seg.DS, "DS"), (Seg.G, "G"), (Seg.SIM, "SIM"), (Seg.T, "T") })
            if (lin >= seg * 16) return $"{name}:{lin - seg * 16:x4}";
        return $"{lin:x5}";
    }

    FuncStats S(string f)
    {
        if (!Stats.TryGetValue(f, out var s)) Stats[f] = s = new FuncStats();
        return s;
    }

    /// <summary>Replay one record. Returns true if it matched.</summary>
    public bool Run(TraceRecord rec)
    {
        var s = S(rec.Func);
        s.Calls++;
        var args = rec.Args.EnumerateArray().ToArray();
        var mi = FindMethod(rec.Func, args.Length);
        if (mi == null)
        {
            s.Missing++;
            return false;
        }
        var st = new State((byte[])rec.Before.Clone()) { Clock = rec.Clock, BiosKbd = rec.Kbd };
        try
        {
            st.Hooks = MakePlayer(rec.Player);
        }
        catch (NotSupportedException ex)
        {
            Note(s, rec, ex.Message);
            s.Bad++;
            return false;
        }
        var ps = mi.GetParameters();
        var call = new object[ps.Length];
        call[0] = st;
        try
        {
            for (int k = 1; k < ps.Length; k++)
                call[k] = k - 1 < args.Length ? Convert(args[k - 1], ps[k].ParameterType) : ps[k].DefaultValue;
        }
        catch (Exception ex)
        {
            Note(s, rec, "args: " + ex.Message);
            s.Bad++;
            return false;
        }
        object ret;
        try
        {
            ret = mi.Invoke(null, call);
        }
        catch (TargetInvocationException tie)
        {
            var inner = tie.InnerException;
            if (rec.Raise != null)
            {
                s.Ok++;
                return true;
            }
            s.Threw++;
            Note(s, rec, $"threw {inner.GetType().Name}: {inner.Message}\n{FirstFrames(inner)}");
            return false;
        }
        var sb = new StringBuilder();
        if (rec.Raise != null) sb.Append($"python raised {rec.Raise}; ");
        bool opaque = rec.Ret.HasValue && rec.Ret.Value.ValueKind == JsonValueKind.Object
                      && rec.Ret.Value.TryGetProperty("$", out var rt) && rt.GetString() != "bytes";
        if (rec.Raise == null && rec.Ret.HasValue && !opaque)
        {
            var want = Raw(rec.Ret.Value);
            var got = Norm(ret);
            if (mi.ReturnType == typeof(void)) got = null;
            if (!Same(want, got)) sb.Append($"return {Show(got)}, expected {Show(want)}; ");
        }
        if (st.Clock != rec.ClockAfter) sb.Append($"clock {st.Clock} expected {rec.ClockAfter}; ");
        if (st.BiosKbd != rec.KbdAfter) sb.Append($"kbd {st.BiosKbd} expected {rec.KbdAfter}; ");
        int nd = 0;
        var diffs = new StringBuilder();
        for (int i = 0; i < State.Size; i++)
        {
            if (st.Mem[i] != rec.After[i])
            {
                if (nd < 8) diffs.Append($"\n      {Describe(i)}: port {st.Mem[i]:x2} expected {rec.After[i]:x2} (before {rec.Before[i]:x2})");
                nd++;
            }
        }
        if (nd > 0) sb.Append($"{nd} bytes differ:{diffs}");
        if (sb.Length == 0)
        {
            s.Ok++;
            return true;
        }
        s.Bad++;
        Note(s, rec, sb.ToString());
        return false;
    }

    static string FirstFrames(Exception ex) =>
        string.Join("\n", (ex.StackTrace ?? "").Split('\n').Take(4).Select(l => "      " + l.Trim()));

    void Note(FuncStats s, TraceRecord rec, string msg)
    {
        if (s.Notes.Count < MaxNotes)
            s.Notes.Add($"#{rec.Index} {rec.Func}({rec.Args}) [{rec.Player}]: {msg}");
    }
}
