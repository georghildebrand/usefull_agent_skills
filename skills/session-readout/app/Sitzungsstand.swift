// Sitzungsstand: a small window that reads a short session summary aloud.
//
// The window and the sound are one process. Closing the window, pressing Stop or
// Cmd+Q ends the process, and the sound ends with it.
//
// Rules:
// - Sound plays only on headphones (Bluetooth, or wired headphones on the built-in jack).
//   If the output changes to anything else, the sound stops at once.
// - Engine "auto": try the local Qwen3 TTS server. If its first sentence is not ready
//   within FIRST_SENTENCE_DEADLINE seconds, use the macOS system voice for everything.
//   A late sound never starts.
// - Only one window at a time: the launcher ends the previous one.
//
// Usage: Sitzungsstand --file <text file, one sentence per line> [--session <label>]
//          [--engine auto|qwen|system] [--tts-url U] [--tts-model M] [--tts-voice V] [--system-lang L]
//          [--system-voice NAME]
//        Sitzungsstand --check   (print output device and TTS server state, no window, no sound)

import AppKit
import AVFoundation
import CoreAudio

let FIRST_SENTENCE_DEADLINE: TimeInterval = 8
let LATER_SENTENCE_DEADLINE: TimeInterval = 20
let CLOSE_AFTER_DONE: TimeInterval = 5
let CLOSE_AFTER_SILENT: TimeInterval = 180

func arg(_ name: String) -> String? {
    let a = CommandLine.arguments
    guard let i = a.firstIndex(of: name), i + 1 < a.count else { return nil }
    return a[i + 1]
}

// `open` does not pass environment variables to an app, so settings come as arguments.
let ttsURL = arg("--tts-url") ?? "http://127.0.0.1:8890/v1"
let ttsModel = arg("--tts-model") ?? "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16"
let ttsVoice = arg("--tts-voice") ?? "Ryan"
let systemLang = arg("--system-lang") ?? "de-DE"
let engineSetting = arg("--engine") ?? "auto"  // auto | qwen | system
let systemVoiceName = arg("--system-voice")  // name or identifier; default = best quality for systemLang

/// The system voice to use: the named one, else the highest quality installed for the language.
func bestSystemVoice() -> AVSpeechSynthesisVoice? {
    let all = AVSpeechSynthesisVoice.speechVoices()
    if let want = systemVoiceName,
       let v = all.first(where: { $0.identifier == want || $0.name.caseInsensitiveCompare(want) == .orderedSame }) {
        return v
    }
    let rank: (AVSpeechSynthesisVoice) -> Int = { $0.quality == .premium ? 2 : $0.quality == .enhanced ? 1 : 0 }
    let lang = all.filter { $0.language == systemLang }
    // Prefer Apple's own voices over the novelty "eloquence" voices at equal quality.
    return lang.max { (rank($0), $0.identifier.contains("eloquence") ? 0 : 1) < (rank($1), $1.identifier.contains("eloquence") ? 0 : 1) }
        ?? AVSpeechSynthesisVoice(language: systemLang)
}
let systemVoice = bestSystemVoice()

func qualityName(_ v: AVSpeechSynthesisVoice?) -> String {
    guard let v else { return "none" }
    return v.quality == .premium ? "premium" : v.quality == .enhanced ? "enhanced" : "default"
}

// MARK: - Headphone check (CoreAudio)

func defaultOutputDevice() -> AudioDeviceID? {
    var dev = AudioDeviceID(0)
    var size = UInt32(MemoryLayout<AudioDeviceID>.size)
    var addr = AudioObjectPropertyAddress(
        mSelector: kAudioHardwarePropertyDefaultOutputDevice,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    let st = AudioObjectGetPropertyData(AudioObjectID(kAudioObjectSystemObject), &addr, 0, nil, &size, &dev)
    return st == noErr && dev != 0 ? dev : nil
}

func deviceUInt32(_ dev: AudioDeviceID, _ sel: AudioObjectPropertySelector, _ scope: AudioObjectPropertyScope) -> UInt32? {
    var value = UInt32(0)
    var size = UInt32(MemoryLayout<UInt32>.size)
    var addr = AudioObjectPropertyAddress(mSelector: sel, mScope: scope, mElement: kAudioObjectPropertyElementMain)
    guard AudioObjectHasProperty(dev, &addr) else { return nil }
    return AudioObjectGetPropertyData(dev, &addr, 0, nil, &size, &value) == noErr ? value : nil
}

func deviceName(_ dev: AudioDeviceID) -> String {
    var name: Unmanaged<CFString>?
    var size = UInt32(MemoryLayout<Unmanaged<CFString>?>.size)
    var addr = AudioObjectPropertyAddress(
        mSelector: kAudioObjectPropertyName,
        mScope: kAudioObjectPropertyScopeGlobal,
        mElement: kAudioObjectPropertyElementMain)
    guard AudioObjectGetPropertyData(dev, &addr, 0, nil, &size, &name) == noErr, let n = name else { return "?" }
    return n.takeRetainedValue() as String
}

/// Returns the device name when the current output is headphones, else nil.
func headphonesName() -> String? {
    guard let dev = defaultOutputDevice(),
          let transport = deviceUInt32(dev, kAudioDevicePropertyTransportType, kAudioObjectPropertyScopeGlobal)
    else { return nil }
    switch transport {
    case kAudioDeviceTransportTypeBluetooth, kAudioDeviceTransportTypeBluetoothLE:
        return deviceName(dev)
    case kAudioDeviceTransportTypeBuiltIn:
        // Built-in output: only the headphone jack counts, never the speakers.
        let hdpn: UInt32 = 0x6864_706E  // 'hdpn'
        if deviceUInt32(dev, kAudioDevicePropertyDataSource, kAudioDevicePropertyScopeOutput) == hdpn {
            return "Kopfhörer (Klinke)"
        }
        return nil
    default:
        return nil
    }
}

// MARK: - App

final class Reader: NSObject, NSApplicationDelegate, NSWindowDelegate, AVAudioPlayerDelegate, AVSpeechSynthesizerDelegate {
    let sentences: [String]
    let session: String
    let created: Date

    var window: NSWindow!
    let statusLabel = NSTextField(labelWithString: "")
    let textView = NSTextView()

    enum Engine { case qwen, system }
    var engine: Engine?
    var audio: [Int: Data] = [:]
    var current = -1
    var player: AVAudioPlayer?
    let synth = AVSpeechSynthesizer()
    var stopped = false
    var waitTimer: Timer?
    var headphoneTimer: Timer?
    var fetchTask: URLSessionDataTask?
    var headphones = ""

    init(sentences: [String], session: String, created: Date) {
        self.sentences = sentences
        self.session = session
        self.created = created
        super.init()
        synth.delegate = self
    }

    // MARK: window

    func applicationDidFinishLaunching(_ n: Notification) {
        buildWindow()
        NSApp.activate(ignoringOtherApps: true)
        guard let hp = headphonesName() else {
            silent("Kein Ton: keine Kopfhörer verbunden. Text nur zum Lesen.")
            return
        }
        headphones = hp
        headphoneTimer = Timer.scheduledTimer(withTimeInterval: 0.3, repeats: true) { [weak self] _ in
            guard let self, !self.stopped else { return }
            if headphonesName() == nil { self.silent("Ton gestoppt: Kopfhörer getrennt.") }
        }
        startEngine()
    }

    func buildWindow() {
        let w: CGFloat = 520, h: CGFloat = 330
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1440, height: 900)
        let frame = NSRect(x: screen.maxX - w - 20, y: screen.maxY - h - 20, width: w, height: h)
        window = NSWindow(contentRect: frame, styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = "Claude · Sitzungsstand vorlesen"
        window.level = .floating
        window.delegate = self
        window.isReleasedWhenClosed = false

        let fmt = DateFormatter()
        fmt.dateFormat = "HH:mm"
        let header = NSTextField(labelWithString: "Sitzung:  \(session)\nErstellt:  \(fmt.string(from: created)) Uhr (Text von Claude, Stimme lokal)")
        header.font = .systemFont(ofSize: 12)
        header.textColor = .secondaryLabelColor
        statusLabel.font = .boldSystemFont(ofSize: 12)
        statusLabel.stringValue = "Bereite Ton vor ..."

        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true
        scroll.documentView = textView
        textView.isEditable = false
        textView.drawsBackground = false
        textView.textContainerInset = NSSize(width: 4, height: 6)
        textView.autoresizingMask = [.width]
        scroll.drawsBackground = false

        let footer = NSTextField(labelWithString: "Schließen, Stopp oder Cmd+Q beendet den Ton sofort.")
        footer.font = .systemFont(ofSize: 11)
        footer.textColor = .tertiaryLabelColor

        let stop = NSButton(title: "Stopp", target: self, action: #selector(stopPressed))
        stop.bezelStyle = .rounded
        stop.keyEquivalent = "\u{1b}"  // Escape also stops

        let top = NSStackView(views: [statusLabel, NSView(), stop])
        top.orientation = .horizontal
        let stack = NSStackView(views: [top, header, scroll, footer])
        stack.orientation = .vertical
        stack.alignment = .leading
        stack.spacing = 8
        stack.edgeInsets = NSEdgeInsets(top: 12, left: 14, bottom: 10, right: 14)
        stack.translatesAutoresizingMaskIntoConstraints = false
        window.contentView = NSView()
        window.contentView!.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: window.contentView!.leadingAnchor),
            stack.trailingAnchor.constraint(equalTo: window.contentView!.trailingAnchor),
            stack.topAnchor.constraint(equalTo: window.contentView!.topAnchor),
            stack.bottomAnchor.constraint(equalTo: window.contentView!.bottomAnchor),
            top.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -28),
            scroll.widthAnchor.constraint(equalTo: stack.widthAnchor, constant: -28),
            scroll.heightAnchor.constraint(greaterThanOrEqualToConstant: 170),
        ])
        renderText()
        window.makeKeyAndOrderFront(nil)
    }

    func renderText() {
        let out = NSMutableAttributedString()
        for (i, s) in sentences.enumerated() {
            let attrs: [NSAttributedString.Key: Any] = [
                .font: i == current ? NSFont.boldSystemFont(ofSize: 14) : NSFont.systemFont(ofSize: 14),
                .foregroundColor: i == current ? NSColor.labelColor : NSColor.secondaryLabelColor,
            ]
            out.append(NSAttributedString(string: s + (i < sentences.count - 1 ? " " : ""), attributes: attrs))
        }
        textView.textStorage?.setAttributedString(out)
    }

    func setStatus(_ s: String) { statusLabel.stringValue = s }

    @objc func stopPressed() { NSApp.terminate(nil) }
    func windowWillClose(_ n: Notification) { NSApp.terminate(nil) }
    func applicationShouldTerminateAfterLastWindowClosed(_ s: NSApplication) -> Bool { true }
    func applicationWillTerminate(_ n: Notification) { halt() }

    /// Stop all sound now. Safe to call more than once.
    func halt() {
        stopped = true
        waitTimer?.invalidate()
        headphoneTimer?.invalidate()
        fetchTask?.cancel()
        player?.stop()
        synth.stopSpeaking(at: .immediate)
    }

    /// Stop sound, keep the text visible, close later.
    func silent(_ reason: String) {
        halt()
        current = -1
        renderText()
        setStatus(reason)
        Timer.scheduledTimer(withTimeInterval: CLOSE_AFTER_SILENT, repeats: false) { _ in NSApp.terminate(nil) }
    }

    func finished() {
        halt()
        current = -1
        renderText()
        setStatus("Fertig. Fenster schließt in \(Int(CLOSE_AFTER_DONE)) Sekunden.")
        Timer.scheduledTimer(withTimeInterval: CLOSE_AFTER_DONE, repeats: false) { _ in NSApp.terminate(nil) }
    }

    // MARK: engines

    func startEngine() {
        if engineSetting == "system" { useSystem(); return }
        // Qwen first; the deadline decides.
        fetch(0)
        waitTimer = Timer.scheduledTimer(withTimeInterval: FIRST_SENTENCE_DEADLINE, repeats: false) { [weak self] _ in
            guard let self, !self.stopped, self.engine == nil else { return }
            self.fetchTask?.cancel()
            if engineSetting == "qwen" {
                self.silent("Kein Ton: lokale Stimme nicht rechtzeitig bereit.")
            } else {
                self.useSystem()
            }
        }
    }

    func fetch(_ i: Int) {
        guard i < sentences.count, !stopped else { return }
        guard let url = URL(string: ttsURL + "/audio/speech") else { return }
        var req = URLRequest(url: url, timeoutInterval: 60)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONSerialization.data(withJSONObject: [
            "model": ttsModel, "input": sentences[i], "voice": ttsVoice, "response_format": "wav",
        ])
        fetchTask = URLSession.shared.dataTask(with: req) { [weak self] data, resp, _ in
            DispatchQueue.main.async {
                guard let self, !self.stopped else { return }
                let ok = (resp as? HTTPURLResponse)?.statusCode == 200 && (data?.count ?? 0) > 1000
                if ok, let data {
                    self.audio[i] = data
                    if i == 0 && self.engine == nil {
                        self.waitTimer?.invalidate()
                        self.engine = .qwen
                        self.playNext()
                    } else if self.engine == .qwen && self.current == i - 1 && self.player == nil {
                        self.playNext()  // we were waiting for this one
                    }
                    self.fetch(i + 1)  // prefetch while playing
                } else if self.engine == nil && engineSetting != "qwen" {
                    self.waitTimer?.invalidate()
                    self.useSystem()  // server down or error: do not wait for the deadline
                } else if self.engine == .qwen {
                    self.switchToSystemFrom(i)
                }
            }
        }
        fetchTask?.resume()
    }

    func useSystem() {
        engine = .system
        playNext()
    }

    func switchToSystemFrom(_ i: Int) {
        engine = .system
        fetchTask?.cancel()
        if player == nil { current = i - 1; playNext() }
    }

    func playNext() {
        guard !stopped else { return }
        player = nil
        current += 1
        guard current < sentences.count else { finished(); return }
        guard headphonesName() != nil else { silent("Ton gestoppt: Kopfhörer getrennt."); return }
        renderText()
        let label = engine == .qwen ? "Stimme Qwen3 \(ttsVoice)" : "Systemstimme \(systemVoice?.name ?? "?")"
        setStatus("▶ Satz \(current + 1) von \(sentences.count) · \(label) · \(headphones)")
        switch engine {
        case .qwen:
            if let data = audio[current], let p = try? AVAudioPlayer(data: data) {
                player = p
                p.delegate = self
                p.play()
            } else {
                // Not fetched yet: wait, but not forever.
                current -= 1
                let waitingFor = current + 1
                waitTimer = Timer.scheduledTimer(withTimeInterval: LATER_SENTENCE_DEADLINE, repeats: false) { [weak self] _ in
                    guard let self, !self.stopped, self.current == waitingFor - 1, self.player == nil else { return }
                    self.switchToSystemFrom(waitingFor)
                }
            }
        case .system:
            let u = AVSpeechUtterance(string: sentences[current])
            u.voice = systemVoice
            synth.speak(u)
        case .none:
            break
        }
    }

    func audioPlayerDidFinishPlaying(_ p: AVAudioPlayer, successfully ok: Bool) {
        waitTimer?.invalidate()
        playNext()  // also after a switch to the system voice mid-text
    }

    func speechSynthesizer(_ s: AVSpeechSynthesizer, didFinish u: AVSpeechUtterance) {
        if engine == .system { playNext() }
    }
}

// MARK: - main

if CommandLine.arguments.contains("--check") {
    let dev = defaultOutputDevice().map(deviceName) ?? "none"
    print("output device: \(dev)")
    print("headphones:    \(headphonesName() ?? "no -> window shows text only, no sound")")
    var ok = false
    if let u = URL(string: ttsURL + "/models") {
        let sem = DispatchSemaphore(value: 0)
        URLSession.shared.dataTask(with: URLRequest(url: u, timeoutInterval: 2)) { _, r, _ in
            ok = (r as? HTTPURLResponse)?.statusCode == 200; sem.signal()
        }.resume()
        _ = sem.wait(timeout: .now() + 3)
    }
    print("tts server:    \(ok ? "answers" : "not reachable -> system voice") (\(ttsURL))")
    print("system voice:  \(systemVoice?.name ?? "none for \(systemLang)") (\(qualityName(systemVoice)))")
    exit(0)
}

guard let path = arg("--file"), let raw = try? String(contentsOfFile: path, encoding: .utf8) else {
    FileHandle.standardError.write("usage: Sitzungsstand --file <text file> [--session <label>]\n".data(using: .utf8)!)
    exit(2)
}
let sentences = raw.split(separator: "\n").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
let created = (try? FileManager.default.attributesOfItem(atPath: path)[.modificationDate] as? Date) ?? Date()

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let reader = Reader(sentences: sentences, session: arg("--session") ?? "unbekannt", created: created)
app.delegate = reader
app.run()
