---
title: "Zed editor keybinding for Vim"
slug: "zed-editor-vim-keybinding"
status: "publish"
categories:
  - name: Technology
  - name: Zed,
tags:
  - name: Technology
  - name: Editor
  - name: Keybinding
  - name: Vim
featured_image: "zed.webp"
featured_alt: "Image by https://blog.stackademic.com/reviewing-zed-the-ide-of-the-future-305d681d990c"
---

# Zed Vim Mode Cheat Sheet

Zed's Vim mode replicates familiar Vim behavior while integrating modern features like semantic navigation and multiple cursors. This cheat sheet summarizes essential shortcuts and settings to help you navigate and edit code efficiently in Zed.

---

## Enabling/Disabling Vim Mode

- **Enable/Disable Vim Mode**: Open the command palette and use `Toggle Vim Mode`.
  - This updates your user settings: `"vim_mode": true` or `false`.

---

## Zed-Specific Features

### Language Server Commands

| Command                                 | Shortcut       |
| --------------------------------------- | -------------- |
| Go to definition                        | `g d`          |
| Go to declaration                       | `g D`          |
| Go to type definition                   | `g y`          |
| Go to implementation                    | `g I`          |
| Rename (change definition)              | `c d`          |
| Go to all references of current word    | `g A`          |
| Find symbol in current file             | `g s`          |
| Find symbol in entire project           | `g S`          |
| Go to next diagnostic                   | `g ]` or `] d` |
| Go to previous diagnostic               | `g [` or `[ d` |
| Show inline error (hover)               | `g h`          |
| Open code actions menu                  | `g .`          |

### Git Commands

| Command                   | Shortcut |
| ------------------------- | -------- |
| Go to next Git change     | `] c`    |
| Go to previous Git change | `[ c`    |

### Tree-Sitter Commands

| Command                      | Shortcut |
| ---------------------------- | -------- |
| Select a smaller syntax node | `] x`    |
| Select a larger syntax node  | `[ x`    |

### Multi-Cursor Commands

| Command                                        | Shortcut |
| ---------------------------------------------- | -------- |
| Add cursor at next occurrence of word          | `g l`    |
| Add cursor at previous occurrence of word      | `g L`    |
| Skip latest selection and add next occurrence  | `g >`    |
| Skip latest selection and add previous         | `g <`    |
| Select all occurrences of the current word     | `g a`    |

### Pane Management

| Command                                  | Shortcut           |
| ---------------------------------------- | ------------------ |
| Open project-wide search                 | `g /`              |
| Open current search excerpt              | `g <space>`        |
| Open search excerpt in a split           | `<ctrl-w> <space>` |
| Go to definition in a split              | `<ctrl-w> g d`     |
| Go to type definition in a split         | `<ctrl-w> g D`     |

---

## Insert Mode Shortcuts

| Command                              | Shortcut         |
| ------------------------------------ | ---------------- |
| Open completion menu                 | `ctrl-x ctrl-o`  |
| Request GitHub Copilot suggestion    | `ctrl-x ctrl-c`  |
| Open inline AI assistant             | `ctrl-x ctrl-a`  |
| Open code actions menu               | `ctrl-x ctrl-l`  |
| Hide all suggestions                 | `ctrl-x ctrl-z`  |

---

## Supported Plugins Features

- **Surround Text Objects**:
  - Yank surround: `ys`
  - Change surround: `cs`
  - Delete surround: `ds`
- **Commenting**:
  - Comment/uncomment selection in visual mode: `gc`
  - Comment/uncomment current line in normal mode: `gcc`
- **Project Panel Shortcuts** (Netrw-like):
  - Navigate: `h`, `j`, `k`, `l`
  - Open file: `o`
  - Open file in new tab: `t`

---

## Command Palette Shortcuts

Access the command palette with `:` in Vim mode. Common Vim commands and aliases are supported.

### File and Window Management

| Command            | Description                                 |
| ------------------ | ------------------------------------------- |
| `:w[rite][!]`      | Save current file                           |
| `:wq[!]`           | Save file and close buffer                  |
| `:q[uit][!]`       | Close buffer                                |
| `:wa[ll][!]`       | Save all open files                         |
| `:wqa[ll][!]`      | Save all files and close all buffers        |
| `:qa[ll][!]`       | Close all buffers                           |
| `:[e]x[it][!]`     | Close buffer                                |
| `:up[date]`        | Save current file                           |
| `:cq`              | Quit Zed completely                         |
| `:vs[plit]`        | Split pane vertically                       |
| `:sp[lit]`         | Split pane horizontally                     |
| `:new`             | New file in horizontal split                |
| `:vne[w]`          | New file in vertical split                  |
| `:tabedit`         | New file in new tab                         |
| `:tabnew`          | New file in new tab                         |
| `:tabn[ext]`       | Go to next tab                              |
| `:tabp[rev]`       | Go to previous tab                          |
| `:tabc[lose]`      | Close current tab                           |

> **Note**: Append `!` to force execution without prompts.

### Ex Commands

| Command         | Description                   |
| --------------- | ----------------------------- |
| `:E[xplore]`    | Open project panel            |
| `:C[ollab]`     | Open collaboration panel      |
| `:Ch[at]`       | Open chat panel               |
| `:A[I]`         | Open AI panel                 |
| `:No[tif]`      | Open notifications panel      |
| `:fe[edback]`   | Open feedback window          |
| `:cl[ist]`      | Open diagnostics window       |
| `:te[rm]`       | Open terminal                 |
| `:Ext[ensions]` | Open extensions window        |

### Navigating Diagnostics

| Command             | Description            |
| ------------------- | ---------------------- |
| `:cn[ext]` or `:ln[ext]` | Go to next diagnostic   |
| `:cp[rev]` or `:lp[rev]` | Go to previous diagnostic |
| `:cc` or `:ll`      | Open errors page        |

### Git Commands

| Command          | Description                                |
| ---------------- | ------------------------------------------ |
| `:dif[fupdate]`  | View diff under cursor (`d o` in normal mode) |
| `:rev[ert]`      | Revert diff under cursor (`d p` in normal mode) |

### Jump Commands

| Command    | Description                           |
| ---------- | ------------------------------------- |
| `:<number>`| Jump to specified line number         |
| `:$`       | Jump to end of file                   |
| `:/foo`    | Jump to next line matching `foo`      |
| `:?foo`    | Jump to previous line matching `foo`  |

### Replacement Commands

| Command               | Description                            |
| --------------------- | -------------------------------------- |
| `:[range]s/foo/bar/`  | Replace `foo` with `bar` in [range]    |

### Editing Commands

| Command       | Description                    |
| ------------- | ------------------------------ |
| `:j[oin]`     | Join current line with next    |
| `:d[elete][l][p]` | Delete current line           |
| `:s[ort] [i]` | Sort selection (case-insensitive with `i`) |
| `:y[ank]`     | Yank (copy) selection or line  |

### Command Mnemonics

- Use mnemonics in the command palette for quick access:
  - `:diffs` – Toggle all diffs
  - `:cpp` – Copy file path
  - `:crp` – Copy relative path
  - `:reveal` – Reveal in Finder
  - `:zlog` – Open Zed log
  - `:clank` – Cancel language server work

---

## Customizing Key Bindings

### Useful Contexts

- **Normal & Visual Mode**: `VimControl && !menu`
- **Normal Mode Only**: `vim_mode == normal && !menu`
- **Insert Mode**: `vim_mode == insert`
- **Empty Pane or Shared Screen**: `EmptyPane || SharedScreen`

### Examples

- **Remap `Shift-Y` to Yank to End of Line**:

  ```json
  {
    "context": "vim_mode == normal && !menu",
    "bindings": {
      "shift-y": ["workspace::SendKeystrokes", "y $"]
    }
  }
  ```

- **Use `jk` to Exit Insert Mode**:

  ```json
  {
    "context": "vim_mode == insert",
    "bindings": {
      "j k": "vim::NormalBefore"
    }
  }
  ```

- **Enable Subword Motions (CamelCase navigation)**:

  ```json
  {
    "context": "VimControl && !menu && vim_mode != operator",
    "bindings": {
      "w": "vim::NextSubwordStart",
      "b": "vim::PreviousSubwordStart",
      "e": "vim::NextSubwordEnd",
      "g e": "vim::PreviousSubwordEnd"
    }
  }
  ```

- **Add Surround in Visual Mode with `Shift-S`**:

  ```json
  {
    "context": "vim_mode == visual",
    "bindings": {
      "shift-s": [
        "vim::PushOperator",
        {
          "AddSurrounds": {}
        }
      ]
    }
  }
  ```

- **Restore Common Editing Shortcuts (Windows/Linux)**:

  ```json
  {
    "context": "Editor && !menu",
    "bindings": {
      "ctrl-c": "editor::Copy",          // Vim default: return to normal mode
      "ctrl-x": "editor::Cut",           // Vim default: decrement
      "ctrl-v": "editor::Paste",         // Vim default: visual block mode
      "ctrl-y": "editor::Undo",          // Vim default: line up
      "ctrl-f": "buffer_search::Deploy", // Vim default: page down
      "ctrl-o": "workspace::Open",       // Vim default: go back
      "ctrl-a": "editor::SelectAll"      // Vim default: increment
    }
  }
  ```

---

## Changing Vim Mode Settings

Modify Vim mode behavior by updating your user settings.

### Available Settings

| Property                      | Description                                                                 | Default Value |
| ----------------------------- | --------------------------------------------------------------------------- | ------------- |
| `use_system_clipboard`        | Clipboard usage: `"always"`, `"never"`, or `"on_yank"`                      | `"always"`    |
| `use_multiline_find`          | If `true`, `f` and `t` motions cross lines                                  | `false`       |
| `use_smartcase_find`          | If `true`, `f` and `t` are case-insensitive with lowercase targets          | `false`       |
| `toggle_relative_line_numbers`| Line numbers relative in normal mode, absolute in insert mode               | `false`       |
| `custom_digraphs`             | Define custom digraphs (e.g., `"fz": "🧟‍♀️"`)                               | `{}`          |

### Example Settings

```json
{
  "vim": {
    "use_system_clipboard": "never",
    "use_multiline_find": true,
    "use_smartcase_find": true,
    "toggle_relative_line_numbers": true,
    "custom_digraphs": {
      "fz": "🧟‍♀️"
    }
  }
}
```

---

## Useful Core Zed Settings for Vim Mode

| Property                  | Description                                           | Default Value        |
| ------------------------- | ----------------------------------------------------- | -------------------- |
| `cursor_blink`            | Enable or disable cursor blinking                     | `true`               |
| `relative_line_numbers`   | Show relative line numbers                            | `true`               |
| `scrollbar`               | Scrollbar display settings (`{"show": "never"}` to hide) | `{"show": "always"}` |
| `scroll_beyond_last_line` | Scroll beyond last line (`"off"` to disable)          | `"one_page"`         |
| `vertical_scroll_margin`  | Lines above/below cursor when scrolling (set to `0` for none) | `3`            |
| `gutter.line_numbers`     | Show line numbers in gutter (`false` to hide)         | `true`               |
| `command_aliases`         | Define aliases for command palette commands           | `{}`                 |

### Example Settings

```json
{
  "cursor_blink": false,
  "relative_line_numbers": true,
  "scrollbar": { "show": "never" },
  "scroll_beyond_last_line": "off",
  "vertical_scroll_margin": 0,
  "gutter": {
    "line_numbers": false
  },
  "command_aliases": {
    "W": "w",
    "Wq": "wq",
    "Q": "q"
  }
}
```

---

## Regex Differences in Search and Replace

- **Capture Groups**: Use `( )` instead of `\(` and `\)`.
- **Matches**: Use `$1`, `$2`, etc., instead of `\1`, `\2`.
- **Global Option**: Searches are global by default; no `/g` needed.
- **Case Sensitivity**:
  - Vim: Use `/i` for case-insensitive.
  - Zed: Add `(?i)` at start or toggle with `alt-cmd-c`.

> **Note**: Zed's command palette adjusts Vim-style substitute commands automatically.

---

For more details on settings and customization, refer to Zed's documentation.
