# Bash completion for layer7 CLI tool

_layer7_completion() {
    local cur prev words cword
    # Initialize standard completion variables
    if declare -F _init_completion >/dev/null 2>&1; then
        _init_completion || return
    else
        # Fallback for systems without _init_completion helper
        COMPREPLY=()
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
    fi

    # Complete options starting with -
    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "--serve --mode --host --port" -- "$cur") )
        return 0
    fi

    # Complete option values
    if [[ "$prev" == "--mode" ]]; then
        COMPREPLY=( $(compgen -W "debug toolkit" -- "$cur") )
        return 0
    fi

    # Find the position of the input script/file argument
    local file_idx=-1
    local i
    for ((i=1; i<cword; i++)); do
        # Ignore arguments that are options or values for options
        if [[ "${words[i]}" != -* ]]; then
            if [[ "${words[i-1]}" == "--mode" || "${words[i-1]}" == "--host" || "${words[i-1]}" == "--port" ]]; then
                continue
            fi
            file_idx=$i
            break
        fi
    done

    # If the user hasn't specified a file yet, suggest files (filtering for .md and .l7)
    if [[ $file_idx -eq -1 ]]; then
        # Try to filter for .md and .l7 files
        local old_extglob=$(shopt -p extglob)
        shopt -s extglob
        COMPREPLY=( $(compgen -f -X '!*@(.md|.l7)' -- "$cur") )
        eval "$old_extglob"
        
        # If no matching markdown files are found, fallback to any file/directory
        if [[ ${#COMPREPLY[@]} -eq 0 ]]; then
            COMPREPLY=( $(compgen -f -- "$cur") )
        fi
        return 0
    fi

    # If a file is selected, determine parameters based on the file type
    local filename="${words[file_idx]}"
    local base_filename=$(basename "$filename")
    local arg_idx=$((cword - file_idx))

    # Smart completion for layer7llama.md parameters
    if [[ "$base_filename" == "layer7llama.md" ]]; then
        case $arg_idx in
            1)
                # First positional arg: model_key
                COMPREPLY=( $(compgen -W "gemma26 gemma31 qwen27 qwencoder30 qwopus qwencodernext" -- "$cur") )
                ;;
            2)
                # Second positional arg: profile
                COMPREPLY=( $(compgen -W "speed accuracy space" -- "$cur") )
                ;;
            3)
                # Third positional arg: vision_toggle
                COMPREPLY=( $(compgen -W "vision_on vision_off" -- "$cur") )
                ;;
        esac
        return 0
    fi

    # Default fallback for other files: standard file completion
    COMPREPLY=( $(compgen -f -- "$cur") )
}

complete -F _layer7_completion layer7
