# Bash completion for layer7llama.md (or layer7llama command)

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

    # Arguments index relative to command
    case $cword in
        1)
            # First argument: model_key
            COMPREPLY=( $(compgen -W "gemma26 gemma31 qwen27 qwencoder30 qwopus qwencodernext" -- "$cur") )
            ;;
        2)
            # Second argument: profile
            COMPREPLY=( $(compgen -W "speed accuracy space" -- "$cur") )
            ;;
        3)
            # Third argument: vision_toggle
            COMPREPLY=( $(compgen -W "vision_on vision_off" -- "$cur") )
            ;;
    esac
    return 0
}

# Register completion for both raw script executions and renamed binary commands
complete -F _layer7llama_completion layer7llama.md layer7llama ./layer7llama.md ./layer7llama
