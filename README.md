# Productivity breacher, how to use/install

# 1. This app is made for MacOS users that struggle with playing games during breaks and making those breaks... a little too long. It's still in beta, but is usable. set your timer (10s,20m,1h or so) and play! 
When it runs out, your gaming apps such as Roblox or Discord are temporarily locked until you set the next timer.
<img width="4480" height="2520" alt="Main App Screenshot" src="https://github.com/user-attachments/assets/94d7645b-9a68-4df3-a35a-378c51d0d87c" />

# 2. Installation process:
when you install the program, you will need to open the .dmg file, then move both apps to the applications folder, then eject the .dmg file, open the apps and you're done. enjoy!
<img width="4480" height="2520" alt="Installation Screenshot" src="https://github.com/user-attachments/assets/58f8b487-f070-43da-8e59-e66dfd0e0b1e" />

# 3. Installation problems:
1) if you try to open it and a pop-up saying "Apple could not verify “Productivity Breacher” is free of malware that may harm your Mac or compromise your privacy" appears, do This:
   <img width="4480" height="2520" alt="Safety Hazard App Screenshot" src="https://github.com/user-attachments/assets/687304f1-8dc6-4298-9876-814f56c4a849" />

  · Press "Done."
  · Open the "System Settings" app, go into "Privacy & Security," scroll down until you see ""Productivity Breacher" was blocked to protect your Mac."
  · Press the "Open Anyway" button right next to the text.
  · The system will ask your Mac password. Enter it. 

2) if you try to open it and a pop-up saying ""Productivity Breacher" is damaged and can't be opened. You should move it to the bin" appears, do this:
   <img width="4480" height="2520" alt="Damaged App screenshot" src="https://github.com/user-attachments/assets/a06679d2-87fc-4357-8967-77ec97f9a25e" />
  · Press "Cancel"
  · Open "Terminal" on your Mac
  · Make sure both the apps are in Applications
  · Paste this command into the Terminal: xattr -cr /Applications/Productivity\ Breacher.app && xattr -cr /Applications/Productivity\ Breacher\ PARENT.app
  · Try to open your apps.
This will open the app, but you should know that it's still in beta, so since you aren't supposed to close it with "Quit" I left several backup options such as a code that your parent sets through the parent app and force quit through Option + Command + Esc.
Enjoy!

# 4. Socket connections:
To let your parent have control over your app via "Productivity Breacher PARENT" do this:
<img width="4480" height="2520" alt="Pb_session_file.json Relocation" src="https://github.com/user-attachments/assets/b289a9ff-a946-4c4c-a276-3dfbd5b61cd2" />
   MAIN:
      · Open "Productivity Breacher".
      · Open a "Finder" window.
      · Press Command + Shift + G
      · Copy this, but change "YOUR_MAC_NAME_HERE" to your actual Mac name (System Settings -> General -> Sharing -> Local Hostname).
         /Users/YOUR_MAC_NAME_HERE/Library/Application Support/ProductivityBreacher/
      · Press "Enter".
      · Find a file named "pb_session.json".
      · Copy it.
      · Send the copied file to your parent's device.
   PARENT:
      · Open a "Finder" window.
      · Press Command + Shift + G
      · Copy this, but change "YOUR_MAC_NAME_HERE" to your actual Mac name.
         /Users/YOUR_MAC_NAME_HERE/Library/Application Support/ProductivityBreacher/
      · Copy the file your child sent you.
      · Relocate the file into the folder you just opened in "Finder".
   Then, open both the apps: main on the child's device, PARENT on the parent's device. Enjoy.

P.S. v2.15 is OUT NOW! Have fun with finding all the secrets, getting used to the new mechanics and overall getting your productivity better! Also, I've got my own discord server! https://discord.gg/8enSRtS7Tq. Updates are weekly at Sundays, 9:00 AM (California). Cya then!
