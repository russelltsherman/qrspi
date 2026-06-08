# cmux keyboard shortcuts

Full keyboard reference for cmux. Keystroke notation and escape sequences are kept inside
code fences so they render and copy cleanly. cmux is macOS-first, so the primary modifier
is the Command key, written `Cmd`. Bindings are customizable — these are the documented
defaults at authoring time; confirm against your installed build (treat mismatches as
version drift, not error).

## Table of contents

- [Notation](#notation)
- [Workspace navigation](#workspace-navigation)
- [Surface (tab) navigation](#surface-navigation)
- [Pane (split) navigation](#pane-navigation)
- [Notifications](#notifications)
- [Claude Code Teams](#claude-code-teams)
- [Customizing bindings](#customizing-bindings)

## Notation

Keystrokes are written inside code fences to avoid any frontmatter/render issues:

```
Cmd+N         press Command and N together
Cmd+Shift+N   press Command, Shift, and N together
Cmd+1 .. Cmd+9 press Command and a digit
```

`Cmd` is the macOS Command key. On non-macOS builds the equivalent modifier may differ;
the multiplexer navigation may map to a different leader.

## Workspace navigation

A workspace is one isolated context — usually one agent task.

```
Cmd+N            new workspace
Cmd+W            close current workspace
Cmd+Shift+]      next workspace
Cmd+Shift+[      previous workspace
Cmd+1 .. Cmd+9   jump to workspace by index
Cmd+Shift+R      rename current workspace
Cmd+P            open workspace switcher / picker
```

Name workspaces (`Cmd+Shift+R`) after the task or ticket — with many agents running, a
named switcher (`Cmd+P`) is the fastest way back to the one that needs you.

## Surface navigation

A surface is a tab inside a workspace (terminal, editor, or in-app browser).

```
Cmd+T            new surface (tab) in current workspace
Cmd+Shift+W      close current surface
Cmd+}            next surface
Cmd+{            previous surface
Cmd+Shift+B      open in-app browser surface
```

## Pane navigation

A pane is a split within a surface — for side-by-side views.

```
Cmd+D            split current pane vertically (left | right)
Cmd+Shift+D      split current pane horizontally (top / bottom)
Cmd+Opt+Arrow    move focus between panes (in arrow direction)
Cmd+Shift+Arrow  resize the current pane
Cmd+Shift+X      close current pane
```

Use panes only when you need two views at once (an agent and a `tail -f`, say). When the
*tool* changes rather than needing both at once, prefer a new surface; when the *context*
changes, prefer a new workspace.

## Notifications

```
Cmd+Shift+M      mute / unmute notifications for the current workspace
Cmd+Opt+N        jump to the workspace of the most recent notification
```

The underlying OSC escape sequences that trigger notifications are documented in
`cli-and-socket-api.md`. For reference, the OSC notification families cmux understands are
written here inside a code fence so the bytes are unambiguous:

```
OSC 9   ; <message>            BEL        # simple notification text
OSC 777 ; notify ; <title> ; <body>  BEL  # title + body notification
OSC 99  ; <metadata> ; <body>   ST       # structured notification
```

where `BEL` is the bell byte (`\a`, hex `07`) and `ST` is the string terminator
(`ESC \`, i.e. hex `1b 5c`). Emit these from any program in a cmux terminal to raise a
desktop notification. Keep such sequences inside code fences only — never in skill
frontmatter, where they would corrupt parsing.

## Claude Code Teams

```
Cmd+Shift+T      start / attach Claude Code Teams in the current workspace
Cmd+Opt+T        cycle focus across teammate splits
```

Teammates appear as native splits (panes/surfaces) so you navigate them with the standard
pane keys above. The Teams integration is macOS-only.

## Customizing bindings

Bindings live in cmux configuration (see the config notes in `cli-and-socket-api.md`). When
rebinding, keep workspace/surface/pane leaders distinct so navigation stays predictable,
and avoid shadowing the agent's own in-terminal shortcuts (for example, a binding that
swallows a key an agent CLI expects). After editing bindings, restart or reload cmux so
the new map takes effect.
