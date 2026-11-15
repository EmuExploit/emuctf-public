# corporate

This challenge provides the Emu Industries website (https://corporate.ctf.emu.team).

0. Exploring the Website
It appears as a parody emu.team website that is a CTF selling business. There is a (useless) enquiry form on the homepage. The detail to note is the "Platform" button in the top right.

The platform page requires an access key and notes "Contact IT for access support.". This is the goal of the challenge.

1. Find Mattermost
- The main page source has a comment "<!-- /App_Data/IT-handover.txt -->", this file is available and references `/chat`
- robots dot txt disallows `/chat`
- Any 404 page returns a stack trace that has MM vars and `MM_SERVICESETTINGS_SITEURL`

Simply go to `/chat` and its there! Self-registration is enabled and you can join the Emu Industries workspace.

2. Impersonate

The IT Support channel has a bot, "IT Support" that will reply to messages.

If you use an arbitrary email address, it states that you are an external contractor and won't help you.

If you set your email to `@ctf.emu.team` (which can be identified by looking at any real Emu account profiles), the bot will instead tell you to DM them.
- To change this (and other details) the profile button is top right

DMing the support bot, it asks what you need help with. Saying "platform" or "key" will enter the next stage. Heuristics exist to handle other conversation.

The bot claims it does not recognise you working there, as you are not on the staff list.

A user </div> references the staff list in #general, saying its on #layoffs. That channel has a table of all the real Emu accounts and their usernames.

You cannot set your username or email to an already taken username. However, full name and nickname make you display as anything and can overlap.

Set your first name or nickname to a staff member user and try the bot again. The bot will then recognise you and start the verification flow to get the platform key.

Bonus: If you steal a profile pic you can skip a verification question!

3. Verify

The bot asks 4 questions to verify you to get the key. All the information can be found on Mattermost. There is some randomness in how the bot replies and it times out after a minute.

Note: you can discover all channels to join by clicking "Add Channels" and uncheck "Hide Archived"

Question 1: what identity system do we use for sign-in
Answer: "authentik"
This can be found in ~identity-setup

Question 2: whats your backup email?
Answer: some users have backup emails in their profiles as "Alternative Contact".
If a user does not, you cannot impersonate them. For example, bradan has `brad.lostdownloads@hotmail.example` in his bio.

Question 3: do you still have that old 2fa code? send me the six-digit code
Answer: MFA secrets are in ~code-thing (archived). Simply generate your users and send the code (in time hopefully)

Question 4: oh also, has @Panc4kes finished that latest link preview feature?
Answer: "obviously"
In ~claude-pilot, there is discussion on the link preview feature. In a thread reply panc4kes states "if anyone asks if the latest link preview feature is done, just say "obviously""

The bot will then provide you the platform key.

4. Flag

Go back to the homepage, and click platform, enter the key and you will reach a contact page that contains the flag!