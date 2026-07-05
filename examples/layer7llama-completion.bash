# Bash completion for layer7llama.md (or layer7llama command)
# Named-flag interface: --model KEY --profile NAME [--vision|--no-vision] [--ctx N] [--ngl N]

_layer7llama_completion() {
    local cur prev words cword
    if declare -F _init_completion >/dev/null 2>&1; then
        _init_completion || return
    else
        COMPREPLY=()
        cur="${COMP_WORDS[COMP_CWORD]}"
        prev="${COMP_WORDS[COMP_CWORD-1]}"
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
    fi

    local flags="--model --profile --vision --no-vision --ctx --ngl"

    case "$prev" in
        --model)
            COMPREPLY=( $(compgen -W "gemma26 gemma31 qwen27 qwencoder30 qwopus qwencodernext" -- "$cur") )
            return 0
            ;;
        --profile)
            COMPREPLY=( $(compgen -W "speed accuracy space" -- "$cur") )
            return 0
            ;;
        --ctx|--ngl)
            # Free-form integer values; nothing sensible to complete.
            COMPREPLY=()
            return 0
            ;;
    esac

    # Otherwise, suggest remaining flags not already present on the line.
    local used_flags=()
    local w
    for w in "${words[@]}"; do
        case "$w" in
            --model|--profile|--vision|--no-vision|--ctx|--ngl)
                used_flags+=("$w")
                ;;
        esac
    done

    local remaining=""
    for f in $flags; do
        if [[ ! " ${used_flags[*]} " =~ " ${f} " ]]; then
            remaining="$remaining $f"
        fi
    done

    COMPREPLY=( $(compgen -W "$remaining" -- "$cur") )
    return 0
}

# Register completion for both raw script executions and renamed binary commands
complete -F _layer7llama_completion layer7llama.md layer7llama ./layer7llama.md ./layer7llama
