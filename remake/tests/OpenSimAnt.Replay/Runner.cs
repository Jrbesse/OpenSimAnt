using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace OpenSimAnt.Replay;

/// <summary>The default trace-replay run (a path per argument, or remake/build/traces). It lives here rather than
/// inline in Program.cs so a test can assert the exit code: a change under tests/OpenSimAnt.Replay needs a test that
/// asserts the exit code, not the printed line. Program.cs returns exactly what Run returns.
/// An empty trace set is a failure (issue #37): "54 traces matched" and "there was nothing to compare" must not
/// share exit code 0, or a fresh clone or a cleaned workdir is a green gate over unverified code.</summary>
public static class ReplayRunner
{
    public static int Run(string[] args, TextWriter output = null)
    {
        output ??= Console.Out;

        var paths = new List<string>();
        string filter = null;
        int notes = 4;
        bool quiet = false;
        bool allowEmpty = false;                                            // B8: a 0/0 row fails the run unless --allow-empty asks for it
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--func") filter = args[++i];
            else if (args[i] == "--notes") notes = int.Parse(args[++i]);
            else if (args[i] == "--quiet") quiet = true;
            else if (args[i] == "--allow-empty") allowEmpty = true;
            else paths.Add(args[i]);
        }
        if (paths.Count == 0) paths.Add(TracePaths.DefaultDir());

        bool allOk = true;
        bool nothingReplayed = false;                                       // some path yielded no trace at all (issue #37)
        var files = new List<string>();
        foreach (var p in paths)
        {
            if (Directory.Exists(p))
            {
                var found = Directory.GetFiles(p, "*.trace").OrderBy(x => x).ToList();
                if (found.Count == 0)                                       // no traces at all: nothing to replay
                {
                    output.WriteLine($"no trace files (*.trace) in {Path.GetFullPath(p)} -- nothing to replay");
                    nothingReplayed = true;
                }
                files.AddRange(found);
            }
            else if (File.Exists(p)) files.Add(p);
            else
            {
                output.WriteLine($"no such trace file or directory: {p} -- nothing to replay");
                nothingReplayed = true;                                     // an explicit path that matches nothing is a mistake, not a pass
            }
        }
        if (nothingReplayed)
        {
            // Only claim the whole run proved nothing when nothing loaded at all; with other traces on the
            // command line that sentence sends a reader chasing a cause that is not there (review 5834608253).
            if (files.Count == 0)
            {
                if (allowEmpty) output.WriteLine("WARNING: --allow-empty: the run above replayed nothing, it proves nothing");
                else output.WriteLine("the trace set is empty -- the replay would pass vacuously (pass --allow-empty if that is deliberate)");
            }
            else if (allowEmpty) output.WriteLine("WARNING: --allow-empty: one or more paths yielded no traces and did not count as a failure");
            else output.WriteLine($"one or more paths yielded no traces -- a path that matches nothing is a mistake, not a pass (the {files.Count} trace file(s) below did load)");
            if (!allowEmpty) allOk = false;                                 // --allow-empty is the deliberate exception, as for B8
        }

        int empty = 0;                                                      // trace files that record no calls (B8)
        foreach (var file in files)
        {
            var rep = new Replayer { MaxNotes = notes };
            foreach (var rec in TraceReader.Read(file))
            {
                if (filter != null && !rec.Func.Contains(filter)) continue;
                rep.Run(rec);
            }
            int calls = rep.Stats.Values.Sum(s => s.Calls), ok = rep.Stats.Values.Sum(s => s.Ok);
            if (calls == 0)                                                 // nothing ran: an empty trace, or a filter that matched nothing
            {
                empty++;
                output.WriteLine(filter == null
                    ? $"{Path.GetFileName(file)}: 0/0 -- WARNING: the file records no calls, this row proves nothing"
                    : $"{Path.GetFileName(file)}: 0/0 with --func '{filter}' -- the filter matched nothing, this row proves nothing");
            }
            else output.WriteLine($"{Path.GetFileName(file)}: {ok}/{calls} OK");
            foreach (var (f, s) in rep.Stats.OrderBy(k => k.Key))
            {
                if (s.Ok == s.Calls && quiet) continue;
                string status = s.Missing > 0 ? "NOT PORTED" : s.Ok == s.Calls ? "ok" : "MISMATCH";
                output.WriteLine($"  {f}: {s.Ok}/{s.Calls} {status}");
                foreach (var n in s.Notes) output.WriteLine("    " + n);
                if (s.Ok != s.Calls) allOk = false;
            }
        }
        if (empty > 0)
        {
            output.WriteLine($"WARNING: {empty} trace file(s) replayed no calls (the 0/0 rows above); they are not evidence -- record a real trace or delete the file");
            if (!allowEmpty) allOk = false;                                 // B8: a 0/0 row is not a pass (--allow-empty is the deliberate exception)
        }
        output.WriteLine(allOk ? "ALL OK" : "SOME FAILURES");
        return allOk ? 0 : 1;
    }
}
