class ClaudeRunner
  Result = Struct.new(:accepted, :rejected)

  PROMPT = "Say hello world".freeze

  ALLOWED = %w[
    ANTHROPIC_API_KEY
    ANTHROPIC_AUTH_TOKEN
    ANTHROPIC_BASE_URL
    ANTHROPIC_CUSTOM_HEADERS
    CLAUDE_CODE_OAUTH_TOKEN
    CLAUDE_CODE_OAUTH_REFRESH_TOKEN
    CLAUDE_CODE_OAUTH_SCOPES
  ].freeze

  BLOCKED_SUBSTRINGS = %w[
    ANTHROPIC BUN CLAUDE BEDROCK VERTEX AWS GOOGLE GEMINI OPENAI
    PROMPT SYSTEM APPEND MCP TOOL AGENT HOOK PERMISSION SETTINGS
    CONFIG_DIR API_KEY AUTH_TOKEN PATH HOME BASH RUBY NODE
  ].freeze
  BLOCKED_EXACT = %w[FLAG PATH HOME].freeze

  BASE_ENV = {
    "PATH" => "/usr/local/bin:/usr/bin:/bin",
    "HOME" => "/tmp/home",
    "LANG" => "C.UTF-8",
  }.freeze

  def self.claude_path
    (ENV["PATH"] || "").split(File::PATH_SEPARATOR).each do |dir|
      candidate = File.join(dir, "claude")
      return candidate if File.executable?(candidate) && !File.directory?(candidate)
    end
    "/usr/local/bin/claude"
  end

  CLAUDE = claude_path

  def self.allowed?(name)
    return true if ALLOWED.include?(name)

    upper = name.upcase
    return false if BLOCKED_EXACT.include?(upper)

    BLOCKED_SUBSTRINGS.none? { |bad| upper.include?(bad) }
  end

  def self.parse_env(raw)
    env = BASE_ENV.dup
    accepted = []
    rejected = []
    raw.to_s.each_line do |line|
      line = line.strip
      next if line.empty? || line.start_with?("#") || !line.include?("=")

      name, value = line.split("=", 2)
      name = name.strip
      next if name.empty?

      if allowed?(name)
        env[name] = value
        accepted << name
      else
        rejected << name
      end
    end
    [env, accepted, rejected]
  end

  def self.run(raw)
    env, accepted, rejected = parse_env(raw)
    begin
      pid = Process.spawn(
        env,
        CLAUDE, "-p", PROMPT,
        "--allowedTools", "",
        "--disallowedTools", "Bash,Edit,Write,Read,Task,WebFetch,WebSearch,NotebookEdit",
        unsetenv_others: true,
        chdir: "/tmp/home",
        in: File::NULL, out: File::NULL, err: File::NULL,
        pgroup: true,
      )
      begin
        Timeout.timeout(25) { Process.waitpid(pid) }
      rescue Timeout::Error
        Process.kill("KILL", -Process.getpgid(pid)) rescue nil
        Process.waitpid(pid) rescue nil
      end
    rescue SystemCallError
    end
    Result.new(accepted, rejected)
  end
end
