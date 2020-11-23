# `largebot`

**Usage**:

```console
$ largebot [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `refresh-all`: Refresh all LargeBot file assignments.
* `refresh-creators`: Refresh file assignments for LargeBot...
* `refresh-qcs`: Refresh file assignments for LargeBot QCs.

## `largebot refresh-all`

Refresh all LargeBot file assignments.

**Usage**:

```console
$ largebot refresh-all [OPTIONS] [LANG] [PHASE] [TASK]
```

**Arguments**:

* `[LANG]`: [default: EN-US]
* `[PHASE]`: [default: _Training]
* `[TASK]`: [default: Intent]

**Options**:

* `-d, --dry-run`: [default: False]
* `--help`: Show this message and exit.

## `largebot refresh-creators`

Refresh file assignments for LargeBot Creators.

**Usage**:

```console
$ largebot refresh-creators [OPTIONS] [LANG] [PHASE] [TASK]
```

**Arguments**:

* `[LANG]`: [default: EN-US]
* `[PHASE]`: [default: _Training]
* `[TASK]`: [default: Intent]

**Options**:

* `-d, --dry-run`: [default: False]
* `--help`: Show this message and exit.

## `largebot refresh-qcs`

Refresh file assignments for LargeBot QCs.

**Usage**:

```console
$ largebot refresh-qcs [OPTIONS] [LANG] [PHASE] [TASK]
```

**Arguments**:

* `[LANG]`: [default: EN-US]
* `[PHASE]`: [default: _Training]
* `[TASK]`: [default: Intent]

**Options**:

* `-d, --dry-run`: [default: False]
* `--help`: Show this message and exit.
