using Formica.Data;
using Formica.Replay;
using Xunit;

namespace Formica.Sim.Tests;

/// <summary>The window layout solver (UiArt.Relayout, f_25595) against the layouts' own stored rectangles: each layout
/// was saved laid out at the rectangle in its header (+10..+16), so solving it there must give every item's stored
/// rectangle back. Needs the player's game files; without them the one row passes.</summary>
public class LayoutTests
{
    const string NoFiles = "(no game files)";

    static string GameDir => Path.GetFullPath(Path.Combine(TracePaths.DefaultDir(), "..", "..", ".."));

    static UiArt ui;

    static UiArt Ui()
    {
        if (ui != null) return ui;
        var files = new OriginalFiles(GameDir);
        return ui = new UiArt(files, new MapArt(files));
    }

    public static IEnumerable<object[]> Windows()
    {
        if (!OriginalFiles.Present(GameDir)) { yield return new object[] { NoFiles }; yield break; }
        foreach (var id in Ui().Layouts.Keys.OrderBy(k => k))
            yield return new object[] { id.ToString() };
    }

    [Theory]
    [MemberData(nameof(Windows))]
    public void SolverGivesStoredRects(string name)
    {
        if (name == NoFiles) return;
        int id = int.Parse(name);
        var w = Ui().Layouts[id];
        var got = Ui().Relayout(id, w.Requested);
        var bad = w.Items.Select((it, i) => (i, want: it.Rect, got: got.Items[i].Rect))
                         .Where(x => x.want != x.got).ToList();
        Assert.True(bad.Count == 0, $"layout {id}: " + string.Join("; ", bad.Select(x => $"item {x.i} want {x.want} got {x.got}")));
    }

    /// <summary>f_6c566 in Load mode: item 0x1602 at zero height moves everything attached below it up 35 px.</summary>
    [Fact]
    public void FileDialogLoadModeShrinks()
    {
        if (!OriginalFiles.Present(GameDir)) return;
        var w = Ui().Layouts[22];
        var it = w.Items[2];
        var got = Ui().Relayout(22, w.Requested, new Dictionary<int, (int, int, int, int)> { [2] = (it.Pos.x, it.Pos.y, it.Size.w, 0) });
        Assert.Equal(w.Rect.bottom - 35, got.Rect.bottom);
        Assert.Equal(w.Items[5].Rect.top - 35, got.Items[5].Rect.top);
        Assert.Equal(w.Items[20].Rect.top - 35, got.Items[20].Rect.top);
    }
}
