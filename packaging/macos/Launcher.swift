import AppKit
import CryptoKit

func shellQuote(_ text: String) -> String { "'" + text.replacingOccurrences(of: "'", with: "'\\''") + "'" }
func command(_ executable: String, _ arguments: [String]) -> (Int32,String) {
    let p=Process(); let pipe=Pipe(); p.executableURL=URL(fileURLWithPath:executable);p.arguments=arguments
    p.standardOutput=pipe;p.standardError=pipe
    var env=ProcessInfo.processInfo.environment
    env["PATH"]="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:"+(env["PATH"] ?? "")
    p.environment=env
    do {try p.run();let data=pipe.fileHandleForReading.readDataToEndOfFile();p.waitUntilExit();return (p.terminationStatus,String(data:data,encoding:.utf8) ?? "")} catch {return (1,error.localizedDescription)}
}

final class Launcher: NSObject, NSApplicationDelegate {
    var window:NSWindow!;var text:NSTextView!;var status:NSTextField!;var language:NSPopUpButton!
    var buttons:[String:NSButton]=[:];var selected="en";var timer:Timer?;var installing=false;var starting=false;var launchAt:TimeInterval=0
    let fm=FileManager.default
    let resources=Bundle.main.resourceURL!
    lazy var version=String(data:try! Data(contentsOf:resources.appendingPathComponent("version.txt")),encoding:.utf8)!.trimmingCharacters(in:.whitespacesAndNewlines)
    lazy var strings=(try! JSONSerialization.jsonObject(with:Data(contentsOf:resources.appendingPathComponent("ui.json")))) as! [String:[String:String]]
    lazy var support:URL = {
        if let test=ProcessInfo.processInfo.environment["MICRODUCK_INSTALLER_TEST_ROOT"] { return URL(fileURLWithPath:test) }
        return fm.homeDirectoryForCurrentUser.appendingPathComponent("Library/Application Support/MicroduckV7RC")
    }()
    lazy var root=support.appendingPathComponent("versions/\(version)/application")
    lazy var installState=support.appendingPathComponent("install-state-\(version).json")
    func t(_ key:String)->String {strings[selected]?[key] ?? key}
    func json(_ url:URL)->[String:Any] {guard let data=try? Data(contentsOf:url),let value=try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return [:]};return value}
    func ready()->Bool {let value=json(root.appendingPathComponent(".install-ready.json"));return value["ready"] as? Bool == true && value["version"] as? String == version}
    func applicationDidFinishLaunching(_ notification:Notification) {
        let locale=Locale.preferredLanguages.first ?? "en"
        if locale.hasPrefix("zh-Hant") || locale.hasPrefix("zh-TW") {selected="zh-TW"} else if locale.hasPrefix("zh") {selected="zh-CN"} else if locale.hasPrefix("ja") {selected="ja"}
        window=NSWindow(contentRect:NSRect(x:0,y:0,width:760,height:610),styleMask:[.titled,.closable,.miniaturizable,.resizable],backing:.buffered,defer:false)
        let stack=NSStackView();stack.orientation = .vertical;stack.spacing=14;stack.edgeInsets=NSEdgeInsets(top:22,left:22,bottom:22,right:22)
        stack.translatesAutoresizingMaskIntoConstraints=false;window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo:window.contentView!.leadingAnchor),stack.trailingAnchor.constraint(equalTo:window.contentView!.trailingAnchor),stack.topAnchor.constraint(equalTo:window.contentView!.topAnchor),stack.bottomAnchor.constraint(equalTo:window.contentView!.bottomAnchor)])
        let heading=NSTextField(labelWithString:"Microduck V7RC  \(version)");heading.font = .boldSystemFont(ofSize:24);stack.addArrangedSubview(heading)
        language=NSPopUpButton();language.addItems(withTitles:["繁體中文","简体中文","English","日本語"]);language.selectItem(at:["zh-TW","zh-CN","en","ja"].firstIndex(of:selected)!);language.target=self;language.action=#selector(changeLanguage);stack.addArrangedSubview(language)
        let scroll=NSScrollView();scroll.hasVerticalScroller=true;scroll.borderType = .bezelBorder
        text=NSTextView();text.isVerticallyResizable=true;text.isHorizontallyResizable=false;text.autoresizingMask=[.width];text.textContainer?.widthTracksTextView=true;text.isEditable=false;text.font = .monospacedSystemFont(ofSize:12,weight:.regular);text.textContainerInset=NSSize(width:12,height:12);scroll.documentView=text
        stack.addArrangedSubview(scroll);scroll.widthAnchor.constraint(equalTo:stack.widthAnchor,constant:-44).isActive=true;scroll.heightAnchor.constraint(greaterThanOrEqualToConstant:330).isActive=true
        status=NSTextField(wrappingLabelWithString:"");stack.addArrangedSubview(status)
        let row=NSStackView();row.spacing=9
        for key in ["check","install","launch","stop","help"] {let b=NSButton(title:key,target:self,action:#selector(action(_:)));b.identifier=NSUserInterfaceItemIdentifier(key);buttons[key]=b;row.addArrangedSubview(b)}
        stack.addArrangedSubview(row);window.center();refresh();window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)
        timer=Timer.scheduledTimer(withTimeInterval:2,repeats:true){[weak self] _ in self?.poll()}
        if ready() && !CommandLine.arguments.contains("--no-auto-launch") {launch()}
    }
    @objc func changeLanguage(){selected=["zh-TW","zh-CN","en","ja"][language.indexOfSelectedItem];refresh()}
    func refresh(){
        window.title=t("title");for (key,b) in buttons {b.title=t(key)}
        var missing:[String]=[]
        if command("/usr/bin/xcode-select",["-p"]).0 != 0 {missing.append("Apple Command Line Tools (Python 3 / Git / C compiler)")}
        for tool in ["cmake","pkg-config"] {if command("/bin/sh",["-c","command -v \(tool)"]).0 != 0 {missing.append(tool+" (Homebrew)")}}
        if missing.contains(where:{$0.contains("Homebrew")}) && !fm.fileExists(atPath:"/opt/homebrew/bin/brew") && !fm.fileExists(atPath:"/usr/local/bin/brew") {missing.append("Homebrew")}
        text.string="\(t("plan"))\n\n\(t("missing")): \(missing.isEmpty ? t("none") : missing.joined(separator:", "))\n\n\(t("downloads"))\n\n\(t("location")):\n\(root.path)\n\n\(t("copy"))\n\n\(t("unsigned"))"
        status.stringValue=ready() ? t("ready") : t("checked");buttons["launch"]?.isEnabled=ready();buttons["stop"]?.isEnabled=ready()
        buttons["install"]?.isEnabled = !installing
    }
    @objc func action(_ sender:NSButton){switch sender.identifier!.rawValue {case "check":refresh();case "install":install();case "launch":launch();case "stop":_ = command("/bin/bash",[root.appendingPathComponent("scripts/desktop").path,"--stop"]);default:NSWorkspace.shared.open(URL(string:resources.appendingPathComponent("how-to.html").absoluteString+"#"+selected)!)}}
    func error(_ value:String){status.stringValue=t("failed");let a=NSAlert();a.messageText=t("error");a.informativeText=value;a.runModal()}
    func openTerminal(_ url:URL){NSWorkspace.shared.open(url)}
    func install(){
        let a=NSAlert();a.messageText=t("confirm");a.informativeText=text.string;a.addButton(withTitle:t("yes"));a.addButton(withTitle:t("no"));guard a.runModal() == .alertFirstButtonReturn else{return}
        do {
            let payload=resources.appendingPathComponent("payload.zip");let expected=try String(contentsOf:resources.appendingPathComponent("payload.sha256"),encoding:.utf8).trimmingCharacters(in:.whitespacesAndNewlines)
            let actual=SHA256.hash(data:try Data(contentsOf:payload)).map{String(format:"%02x",$0)}.joined();guard expected==actual else{throw NSError(domain:"Payload integrity",code:1)}
            try fm.createDirectory(at:support,withIntermediateDirectories:true)
            if fm.fileExists(atPath:root.path) {
                guard json(root.appendingPathComponent(".installer-source.json"))["version"] as? String == version else{throw NSError(domain:"Target is not owned by this installer",code:2)}
            } else {
                try fm.createDirectory(at:root,withIntermediateDirectories:true)
                let result=command("/usr/bin/ditto",["-x","-k",payload.path,root.path]);guard result.0==0 else{throw NSError(domain:result.1,code:3)}
            }
            try JSONSerialization.data(withJSONObject:["version":version,"ready":false]).write(to:root.appendingPathComponent(".install-ready.json"),options:.atomic)
            let helper=support.appendingPathComponent("install-helper-\(version).command")
            if fm.fileExists(atPath:helper.path){try fm.removeItem(at:helper)}
            try fm.copyItem(at:resources.appendingPathComponent("install.command"),to:helper)
            let wrapper=support.appendingPathComponent("install-\(version).command")
            try ("#!/bin/bash\nexec /bin/bash "+[helper.path,root.path,version,installState.path].map(shellQuote).joined(separator:" ")+"\n").write(to:wrapper,atomically:true,encoding:.utf8)
            try fm.setAttributes([.posixPermissions:0o755],ofItemAtPath:wrapper.path)
            try JSONSerialization.data(withJSONObject:["status":"installing"]).write(to:installState,options:.atomic)
            installing=true;buttons["install"]?.isEnabled=false;buttons["launch"]?.isEnabled=false;status.stringValue=t("working");openTerminal(wrapper)
        } catch {self.error(error.localizedDescription)}
    }
    func finishIcons() throws {
        let applications=fm.homeDirectoryForCurrentUser.appendingPathComponent("Applications");try fm.createDirectory(at:applications,withIntermediateDirectories:true)
        let installed=applications.appendingPathComponent("Microduck V7RC-\(version).app")
        if installed.standardizedFileURL != Bundle.main.bundleURL.standardizedFileURL && !fm.fileExists(atPath:installed.path) {try fm.copyItem(at:Bundle.main.bundleURL,to:installed)}
        let desktop=fm.homeDirectoryForCurrentUser.appendingPathComponent("Desktop/Microduck V7RC.app")
        if fm.fileExists(atPath:desktop.path) {
            guard let previous=try? fm.destinationOfSymbolicLink(atPath:desktop.path), Bundle(url:URL(fileURLWithPath:previous))?.bundleIdentifier==Bundle.main.bundleIdentifier else{throw NSError(domain:"Desktop shortcut already exists; it was not overwritten",code:4)}
            try fm.removeItem(at:desktop)
        }
        try fm.createSymbolicLink(at:desktop,withDestinationURL:installed)
    }
    func launch(){
        guard ready() else{refresh();return}
        let session=json(root.appendingPathComponent(".runtime/desktop-session.json"))
        if session["status"] as? String == "running" && Date().timeIntervalSince1970-(session["updated"] as? Double ?? 0)<3 {status.stringValue=t("running");return}
        let result=command("/usr/bin/python3",[root.appendingPathComponent("scripts/verify-installation.py").path]);guard result.0==0 else{error(result.1);return}
        do {
            let file=support.appendingPathComponent("launch-\(version).command")
            try ("#!/bin/bash\ncd "+shellQuote(root.path)+"\nexec scripts/desktop\n").write(to:file,atomically:true,encoding:.utf8)
            try fm.setAttributes([.posixPermissions:0o755],ofItemAtPath:file.path);starting=true;launchAt=Date().timeIntervalSince1970;status.stringValue=t("working");openTerminal(file)
        } catch {self.error(error.localizedDescription)}
    }
    func poll(){
        if installing {let state=json(installState)["status"] as? String
            if state=="complete" {installing=false;refresh();if ready(){do{try finishIcons();status.stringValue=t("complete")}catch{self.error(error.localizedDescription)}}else{error(t("failed"))}}
            else if state=="failed" {installing=false;refresh();status.stringValue=t("failed")}
        }
        if starting {let state=json(root.appendingPathComponent(".runtime/desktop-session.json"));guard (state["updated"] as? Double ?? 0) >= launchAt else {return};if state["status"] as? String == "running" {status.stringValue=t("running");starting=false}else if state["status"] as? String == "failed" {starting=false;error(state["error"] as? String ?? t("failed"))}}
    }
    func applicationShouldTerminateAfterLastWindowClosed(_ sender:NSApplication)->Bool{true}
}

if CommandLine.arguments.contains("--self-test") {
    precondition(shellQuote("a'b") == "'a'\\''b'")
    print("PASS: native launcher quoting and executable startup")
} else {
    let app=NSApplication.shared;let delegate=Launcher();app.delegate=delegate;app.setActivationPolicy(.regular);app.run()
}
