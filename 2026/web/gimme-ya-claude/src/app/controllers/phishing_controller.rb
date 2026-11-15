class PhishingController < ApplicationController
  layout false

  def index
    @env_text = ""
    @note = "".html_safe
    render :index
  end

  def create
    @env_text = params[:env].to_s
    result = ClaudeRunner.run(@env_text)

    details = +""
    details << "Applied: #{result.accepted.sort.join(', ')}\n" unless result.accepted.empty?
    unless result.rejected.empty?
      details << "Ignored (not allowed): #{result.rejected.sort.join(', ')}\n"
    end

    @note = (%{<div class="note">Thank you for giving us your claude creds :)\n\n} +
             ERB::Util.html_escape(details) + "</div>").html_safe
    render :index
  end
end
