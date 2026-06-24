#!/usr/bin/env ruby
# ==============================================================================
# Layer7 Execution Engine (v0.6.0) - Cognitive-First Implementation
#
# This engine is structured as a narrative: parse → plan → generate → execute → cleanup
# Each section is a single cohesive step, broken into ≤7-line functions.
# ==============================================================================
require 'json'
require 'open3'
require 'fileutils'

# ------------------------------------------------------------------------------
# ## Validate Environment
# ------------------------------------------------------------------------------
LAYER7_DIR = "/tmp/layer7_run_#{Time.now.to_i}"
FileUtils.mkdir_p(LAYER7_DIR)

def validate_environment
  if ARGV.length < 2
    puts "Usage: ./layer7.rb <module.md> <input_args...>"
    exit 1
  end

  [ARGV[0], ARGV[1]]
end

md_file, input_arg = validate_environment
md_content = File.read(md_file)

# State structure: { "canonicalid" => { val: "raw string", var_name: "SafeName" } }
global_state = {}
puts "=== Layer7 v0.6.0 Execution Engine ==="

# ------------------------------------------------------------------------------
# ## Identifier Normalization
# ------------------------------------------------------------------------------
def canonical_id(str)
  # Collapses to lowercase alphanumeric for fuzzy matching
  str.to_s.strip.gsub(/[^a-zA-Z0-9]/, '').downcase
end

def var_name(str)
  # Converts "The Tickets" -> "TheTickets" for safe variable names
  str.to_s.strip.gsub(/\s+/, '').gsub(/[^a-zA-Z0-9_]/, '')
end

# ------------------------------------------------------------------------------
# ## Parse Module Into Execution Plan
# ------------------------------------------------------------------------------
def extract_chunks(md_content)
  chunks = []
  # Match: ## Header Name => Output <= Input ```lang\ncode```
  md_content.scan(/^(##?\s+([^`\n]+)).*?```(\w+)\n(.*?)```/m).each do |match|
    _, raw_header, lang, code = match
    chunks << parse_chunk(raw_header, lang, code)
  end
  chunks
end

def parse_chunk(raw_header, lang, code)
  display_name = extract_display_name(raw_header)
  {
    display_name: display_name,
    canonical_name: canonical_id(display_name),
    lang: lang.downcase.strip,
    code: code,
    stdin_raw: extract_stdin_raw(raw_header),
    stdin_sym: extract_stdin(raw_header),
    stdout_raw: extract_stdout_raw(raw_header),
    stdout_sym: extract_stdout(raw_header)
  }
end

def extract_display_name(raw_header)
  # Strip redirection operators to get the chunk name
  raw_header.split(/(<=|=>)/).first.strip
end

def extract_stdin(raw_header)
  # Extract <= Target (input source), return nil if no match
  target = raw_header.match(/<=\s*([^=]+?)(?=\s*=>|$)/)&.captures&.first&.strip
  target ? canonical_id(target) : nil
end

def extract_stdin_raw(raw_header)
  # Keep original casing for variable naming
  raw_header.match(/<=\s*([^=]+?)(?=\s*=>|$)/)&.captures&.first&.strip
end

def extract_stdout(raw_header)
  # Extract => Target (output destination), return nil if no match
  target = raw_header.match(/=>\s*([^=]+?)(?=\s*<=|$)/)&.captures&.first&.strip
  target ? canonical_id(target) : nil
end

def extract_stdout_raw(raw_header)
  # Keep original casing for variable naming
  raw_header.match(/=>\s*([^=]+?)(?=\s*<=|$)/)&.captures&.first&.strip
end

chunks = extract_chunks(md_content)

# ------------------------------------------------------------------------------
# ## Build Execution Plan
# ------------------------------------------------------------------------------
def build_execution_plan(chunks, global_state)
  rpc_wrappers = {}
  executable_chunks = []

  chunks.each do |chunk|
    if data_chunk?(chunk)
      register_data_slot(chunk, global_state)
    else
      executable_chunks << chunk
      register_rpc_wrapper(chunk, rpc_wrappers) if pure_js_function?(chunk)
    end
  end

  [executable_chunks, rpc_wrappers]
end

def data_chunk?(chunk)
  ['json', 'yaml', 'yml'].include?(chunk[:lang])
end

def register_data_slot(chunk, global_state)
  global_state[chunk[:canonical_name]] = {
    val: chunk[:code].strip,
    var_name: var_name(chunk[:display_name])
  }
end

def pure_js_function?(chunk)
  ['javascript', 'js'].include?(chunk[:lang]) &&
  chunk[:code].strip.start_with?('function')
end

def register_rpc_wrapper(chunk, rpc_wrappers)
  wrapper_path = "#{LAYER7_DIR}/#{var_name(chunk[:display_name])}_rpc.js"
  File.write(wrapper_path, generate_js_wrapper(chunk[:code]))
  rpc_wrappers[chunk[:display_name]] = wrapper_path
end

def generate_js_wrapper(code)
  # Wraps a pure JS function for subprocess RPC calls
  <<~JS
    const func = #{code.strip};
    const input = JSON.parse(process.argv[2] || '{}');
    console.log(func(input));
  JS
end

executable_chunks, rpc_wrappers = build_execution_plan(chunks, global_state)

# ------------------------------------------------------------------------------
# ## Generate Language Preambles
# ------------------------------------------------------------------------------
def generate_preamble(lang, global_state, rpc_wrappers)
  case lang
  when 'perl'   then generate_perl_preamble(global_state, rpc_wrappers)
  when 'python' then generate_python_preamble(global_state)
  else ""
  end
end

def generate_perl_preamble(state, rpc_wrappers)
  declarations = declare_perl_variables(state)
  payloads = inject_perl_payloads(state)
  wrappers = inject_perl_rpc_wrappers(rpc_wrappers)

  "use JSON;\nuse strict;\nuse warnings;\n\n" +
  declarations + payloads + wrappers
end

def declare_perl_variables(state)
  # Declare all variables upfront to satisfy 'use strict'
  state.map { |_, data| "my $#{data[:var_name]};\n" }.join
end

def inject_perl_payloads(state)
  # Inject JSON data as deserialized Perl structures
  state.map do |canonical, data|
    next if data[:val].nil? || data[:val].empty?
    <<~PERL
      my $raw_#{canonical} = <<'__L7__';
      #{data[:val]}
      __L7__
      $#{data[:var_name]} = decode_json($raw_#{canonical});
    PERL
  end.join("\n")
end

def inject_perl_rpc_wrappers(rpc_wrappers)
  # Generate Perl subroutines that shell out to JS via Node
  rpc_wrappers.map do |display_name, rpc_path|
    <<~PERL
      sub #{var_name(display_name)} {
        my ($arg) = @_;
        my $json = encode_json($arg);
        $json =~ s/'/'\\\\''/g;
        my $res = `node #{rpc_path} '$json'`;
        return $res =~ /true/i ? 1 : 0;
      }
    PERL
  end.join("\n")
end

def generate_python_preamble(state)
  # Inject JSON data as deserialized Python structures
  preamble = "import json\n"
  state.each do |_, data|
    next if data[:val].nil? || data[:val].empty?
    preamble += "#{data[:var_name]} = json.loads(r\"\"\"#{data[:val]}\"\"\")\n"
  end
  preamble
end

# ------------------------------------------------------------------------------
# ## Execute Chunks
# ------------------------------------------------------------------------------
def execute_chunks(executable_chunks, global_state, input_arg, rpc_wrappers)
  executable_chunks.each do |chunk|
    next if skip_pure_function?(chunk)

    puts "\n>> Running: #{chunk[:display_name]} [#{chunk[:lang]}]"
    script_path = write_chunk_script(chunk, global_state, rpc_wrappers)
    stdout = run_chunk(chunk, script_path, global_state, input_arg)
    capture_output(chunk, stdout, global_state)
  end
end

def skip_pure_function?(chunk)
  # Pure JS functions are registered as RPC wrappers, not executed directly
  if pure_js_function?(chunk)
    puts "[-] Layer 7: Registered Callable [#{chunk[:display_name]}]"
    true
  else
    false
  end
end

def write_chunk_script(chunk, global_state, rpc_wrappers)
  script_path = "#{LAYER7_DIR}/#{var_name(chunk[:display_name])}.#{chunk[:lang]}"
  preamble = generate_preamble(chunk[:lang], global_state, rpc_wrappers)
  File.write(script_path, preamble + "\n" + chunk[:code])
  script_path
end

def run_chunk(chunk, script_path, global_state, input_arg)
  cmd = build_command(chunk, script_path, input_arg)
  stdin_data = route_stdin(chunk, global_state, input_arg)

  stdout, stderr, status = Open3.capture3(cmd, stdin_data: stdin_data)
  handle_execution_result(chunk, status, stderr, stdout)
end

def build_command(chunk, script_path, input_arg)
  case chunk[:lang]
  when 'bash', 'sh' then "bash #{script_path} #{input_arg}"
  when 'perl'       then "perl #{script_path}"
  when 'python'     then "python3 #{script_path}"
  end
end

def route_stdin(chunk, global_state, input_arg)
  # Route data from state or command-line args
  if chunk[:stdin_sym] && global_state.key?(chunk[:stdin_sym])
    global_state[chunk[:stdin_sym]][:val]
  elsif ['bash', 'sh'].include?(chunk[:lang])
    input_arg
  else
    ""
  end
end

def handle_execution_result(chunk, status, stderr, stdout)
  if status.success?
    stdout
  else
    puts "\n[!] Layer7 Execution Halted at chunk: #{chunk[:display_name]}"
    puts "Process exited with code #{status.exitstatus}"
    puts "STDERR:\n#{stderr}"
    exit(status.exitstatus)
  end
end

def capture_output(chunk, stdout, global_state)
  if chunk[:stdout_sym]
    puts "   => Redirection captured into State: [#{chunk[:stdout_raw]}]"
    global_state[chunk[:stdout_sym]] = {
      val: stdout.strip,
      var_name: var_name(chunk[:stdout_raw])
    }
  else
    puts stdout unless stdout.strip.empty?
  end
end

execute_chunks(executable_chunks, global_state, input_arg, rpc_wrappers)

# ------------------------------------------------------------------------------
# ## Teardown
# ------------------------------------------------------------------------------
puts "\n=== Layer7 Pipeline Finished ==="
FileUtils.rm_rf(LAYER7_DIR)
