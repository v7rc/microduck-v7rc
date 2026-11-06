using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Windows;
using System.Windows.Controls;

namespace MicroduckV7RC;

static class Assets {
    public static byte[] Read(string name) {using var s=Assembly.GetExecutingAssembly().GetManifestResourceStream(name) ?? throw new InvalidOperationException("Missing resource: "+name);using var b=new MemoryStream();s.CopyTo(b);return b.ToArray();}
    public static string Text(string name)=>Encoding.UTF8.GetString(Read(name)).Trim();
    public static string Version=>Text("version.txt");
    public static void ValidatePayload() {var expected=Text("payload.sha256");var actual=Convert.ToHexString(SHA256.HashData(Read("payload.zip"))).ToLowerInvariant();if(expected!=actual)throw new InvalidDataException("Payload SHA256 mismatch");}
}

record Result(int Code,string Output);
static class Commands {
    public static ProcessStartInfo Info(string exe,IEnumerable<string> args,bool capture) {
        var p=new ProcessStartInfo(exe){UseShellExecute=false,RedirectStandardOutput=capture,RedirectStandardError=capture,CreateNoWindow=capture};
        foreach(var arg in args)p.ArgumentList.Add(arg);
        p.Environment["WSL_UTF8"]="1";return p;
    }
    public static async Task<Result> Run(string exe,IEnumerable<string> args,int seconds=30) {
        using var p=Process.Start(Info(exe,args,true)) ?? throw new IOException("Cannot start "+exe);
        var output=p.StandardOutput.ReadToEndAsync();var errors=p.StandardError.ReadToEndAsync();
        using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(seconds));
        try{await p.WaitForExitAsync(timeout.Token);}catch(OperationCanceledException){p.Kill(true);throw new TimeoutException("Command timed out; Ubuntu may need first-run initialization");}
        return new(p.ExitCode,((await output)+"\n"+(await errors)).Replace("\0","").Trim());
    }
    public static string[] WslCommand(string distro,string root,string action)=>new[]{"--distribution",distro,"--cd",root,"--","bash","scripts/desktop"}.Concat(action=="stop"?new[]{"--stop"}:Array.Empty<string>()).ToArray();
}

sealed class Launcher:Window {
    readonly Dictionary<string,Dictionary<string,string>> strings=JsonSerializer.Deserialize<Dictionary<string,Dictionary<string,string>>>(Assets.Text("ui.json"))!;
    readonly string[] languages={"zh-TW","zh-CN","en","ja"};string selected="en";
    readonly string distro="Ubuntu-24.04";
    readonly string local=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs","MicroduckV7RC");
    readonly TextBox plan=new(){IsReadOnly=true,AcceptsReturn=true,TextWrapping=TextWrapping.Wrap,VerticalScrollBarVisibility=ScrollBarVisibility.Auto,MinHeight=330,Margin=new Thickness(0,12,0,12)};
    readonly TextBlock status=new(){TextWrapping=TextWrapping.Wrap,Margin=new Thickness(0,8,0,8)};
    readonly Dictionary<string,Button> buttons=new();bool ubuntu=false,initialized=false,ready=false,busy=false;string linuxHome="",root="";
    string T(string key)=>strings[selected].GetValueOrDefault(key,key);
    public Launcher() {
        Width=860;Height=650;MinWidth=720;MinHeight=550;WindowStartupLocation=WindowStartupLocation.CenterScreen;
        var locale=System.Globalization.CultureInfo.CurrentUICulture.Name;
        selected=locale.StartsWith("zh-TW")||locale.StartsWith("zh-HK")?"zh-TW":locale.StartsWith("zh")?"zh-CN":locale.StartsWith("ja")?"ja":"en";
        var panel=new DockPanel{Margin=new Thickness(22)};Content=panel;
        var top=new StackPanel();DockPanel.SetDock(top,Dock.Top);panel.Children.Add(top);
        top.Children.Add(new TextBlock{Text="Microduck V7RC  "+Assets.Version,FontSize=24,FontWeight=FontWeights.Bold});
        var language=new ComboBox{ItemsSource=new[]{"繁體中文","简体中文","English","日本語"},SelectedIndex=Array.IndexOf(languages,selected),Width=180,HorizontalAlignment=HorizontalAlignment.Left,Margin=new Thickness(0,12,0,0)};
        language.SelectionChanged+=async(_,_)=>{selected=languages[language.SelectedIndex];if(!busy)await Check(false);};top.Children.Add(language);
        var bottom=new StackPanel();DockPanel.SetDock(bottom,Dock.Bottom);panel.Children.Add(bottom);bottom.Children.Add(status);
        var row=new WrapPanel();bottom.Children.Add(row);
        foreach(var key in new[]{"check","install","launch","stop","help"}) {var b=new Button{Content=key,Padding=new Thickness(12,7,12,7),Margin=new Thickness(0,0,9,4)};buttons[key]=b;row.Children.Add(b);b.Click+=async(_,_)=>await Action(key);}
        panel.Children.Add(plan);
        Loaded+=async(_,_)=>{await Check(false);if(ready&&!Environment.GetCommandLineArgs().Contains("--no-auto-launch"))await Launch();};
    }
    void Labels(){Title=T("title");foreach(var (key,b) in buttons)b.Content=T(key);}
    void SetBusy(bool value){busy=value;foreach(var (key,b) in buttons)b.IsEnabled=!value&&(key!="launch"||ready);status.Text=value?T("working"):ready?T("ready"):T("waiting");}
    async Task Check(bool report) {
        SetBusy(true);Labels();ubuntu=false;initialized=false;ready=false;
        var details=new StringBuilder(T("plan")+"\n\n"+T("wsl")+"\n\n"+T("downloads"));
        try{
            var list=await Commands.Run("wsl.exe",new[]{"--list","--quiet"});
            ubuntu=list.Code==0&&list.Output.Split('\n',StringSplitOptions.TrimEntries|StringSplitOptions.RemoveEmptyEntries).Contains(distro);
            if(ubuntu) {
                var id=await Commands.Run("wsl.exe",new[]{"-d",distro,"--","id","-u"},15);
                initialized=id.Code==0&&id.Output.Trim()!="0";
                if(initialized) {
                    var home=await Commands.Run("wsl.exe",new[]{"-d",distro,"--","printenv","HOME"});
                    if(home.Code!=0||!home.Output.StartsWith('/'))throw new IOException("Cannot determine Linux home");
                    linuxHome=home.Output.Trim();root=linuxHome+"/.local/share/microduck-v7rc/versions/"+Assets.Version+"/application";
                    var receipt=await Commands.Run("wsl.exe",new[]{"-d",distro,"--","cat",root+"/.install-ready.json"});
                    if(receipt.Code==0) {using var doc=JsonDocument.Parse(receipt.Output);ready=doc.RootElement.GetProperty("ready").GetBoolean()&&doc.RootElement.GetProperty("version").GetString()==Assets.Version;}
                    var packages=await Commands.Run("wsl.exe",new[]{"-d",distro,"--","bash","-c","for p in git curl python3 build-essential cmake pkg-config libssl-dev libudev-dev libasound2-dev libgl1 libegl1 libgl1-mesa-dri libglfw3 unzip; do dpkg-query -W -f='${Status}' \"$p\" 2>/dev/null | grep -qx 'install ok installed' || printf '%s ' \"$p\"; done"});
                    details.Append("\n\n"+T("missing")+": "+(packages.Output.Length==0?T("none"):packages.Output));
                    details.Append("\n\n"+T("location")+":\n"+root);
                } else details.Append("\n\n"+T("initialize"));
            }
        }catch(Exception e){details.Append("\n\n"+e.Message);if(report)MessageBox.Show(e.Message,T("error"));}
        details.Append("\n\n"+T("next")+"\n\n"+T("copy")+"\n\n"+T("unsigned"));plan.Text=details.ToString();SetBusy(false);status.Text=ready?T("ready"):T("checked");
    }
    async Task Action(string key) {try{switch(key){case "check":await Check(true);break;case "install":await Install();break;case "launch":await Launch();break;case "stop":if(root.Length>0)await Commands.Run("wsl.exe",Commands.WslCommand(distro,root,"stop"));break;default:Directory.CreateDirectory(local);var guide=Path.Combine(local,"how-to.html");File.WriteAllBytes(guide,Assets.Read("how-to.html"));foreach(var lang in languages)File.WriteAllBytes(Path.Combine(local,"INSTALL."+lang+".md"),Assets.Read("INSTALL."+lang+".md"));Process.Start(new ProcessStartInfo(new Uri(guide).AbsoluteUri+"#"+selected){UseShellExecute=true});break;}}catch(Exception e){SetBusy(false);status.Text=T("failed");MessageBox.Show(e.Message,T("error"));}}
    void Materialize() {
        Assets.ValidatePayload();Directory.CreateDirectory(local);
        foreach(var name in new[]{"payload.zip","payload.sha256","install-linux.sh","app-icon.ico"})File.WriteAllBytes(Path.Combine(local,name),Assets.Read(name));
        File.WriteAllText(Path.Combine(local,"install-linux.sh"),Encoding.UTF8.GetString(Assets.Read("install-linux.sh")).Replace("\r\n","\n"),new UTF8Encoding(false));
        var self=Environment.ProcessPath!;var destination=Path.Combine(local,"MicroduckV7RC.exe");
        if(!Path.GetFullPath(self).Equals(Path.GetFullPath(destination),StringComparison.OrdinalIgnoreCase)) {
            if(File.Exists(destination)&&FileVersionInfo.GetVersionInfo(destination).ProductVersion!=FileVersionInfo.GetVersionInfo(self).ProductVersion)throw new IOException("A different launcher version exists; keep it and choose a new install folder");
            if(!File.Exists(destination))File.Copy(self,destination);
        }
    }
    async Task Install() {
        if(MessageBox.Show(plan.Text,T("confirm"),MessageBoxButton.YesNo,MessageBoxImage.Question)!=MessageBoxResult.Yes)return;
        Materialize();SetBusy(true);
        if(!ubuntu) {
            var text="wsl.exe --install --distribution Ubuntu-24.04 --no-launch";
            var elevated=new ProcessStartInfo("powershell.exe"){UseShellExecute=true,Verb="runas"};
            foreach(var a in new[]{"-NoProfile","-EncodedCommand",Convert.ToBase64String(Encoding.Unicode.GetBytes(text))})elevated.ArgumentList.Add(a);
            Process.Start(elevated);SetBusy(false);status.Text=T("reboot");return;
        }
        if(!initialized) {Process.Start(Commands.Info("wsl.exe",new[]{"-d",distro},false));SetBusy(false);status.Text=T("initialize");return;}
        var linuxPayload=await Commands.Run("wsl.exe",new[]{"-d",distro,"--","wslpath","-u",Path.Combine(local,"payload.zip")});
        var linuxScript=await Commands.Run("wsl.exe",new[]{"-d",distro,"--","wslpath","-u",Path.Combine(local,"install-linux.sh")});
        if(linuxPayload.Code!=0||linuxScript.Code!=0)throw new IOException("Cannot map installer resources into WSL");
        using var process=Process.Start(Commands.Info("wsl.exe",new[]{"-d",distro,"--","bash",linuxScript.Output.Trim(),linuxPayload.Output.Trim(),root,Assets.Version,"--approved"},false)) ?? throw new IOException("Cannot start Ubuntu installer");
        await process.WaitForExitAsync();
        if(process.ExitCode!=0)throw new IOException(T("failed")+" Exit code "+process.ExitCode);
        await Check(false);
        if(!ready)throw new IOException("Setup exited but no verified ready receipt exists");
        CreateShortcut();status.Text=T("complete");
    }
    void CreateShortcut() {
        var desktop=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"Microduck V7RC.lnk");
        var type=Type.GetTypeFromProgID("WScript.Shell") ?? throw new IOException("Windows shortcut service unavailable");
        dynamic shell=Activator.CreateInstance(type)!;dynamic shortcut=shell.CreateShortcut(desktop);
        if(File.Exists(desktop)&&!string.Equals((string)shortcut.TargetPath,Path.Combine(local,"MicroduckV7RC.exe"),StringComparison.OrdinalIgnoreCase))throw new IOException("An unrelated desktop shortcut already exists; it was not overwritten");
        shortcut.TargetPath=Path.Combine(local,"MicroduckV7RC.exe");shortcut.WorkingDirectory=local;shortcut.IconLocation=Path.Combine(local,"app-icon.ico");shortcut.Description="Microduck V7RC";shortcut.Save();
    }
    async Task Launch() {
        if(!ready)return;
        var verify=await Commands.Run("wsl.exe",new[]{"-d",distro,"--cd",root,"--","python3","scripts/verify-installation.py"});
        if(verify.Code!=0)throw new IOException(verify.Output);
        var previous=await Commands.Run("wsl.exe",new[]{"-d",distro,"--","cat",root+"/.runtime/desktop-session.json"});
        if(previous.Code==0) {using var old=JsonDocument.Parse(previous.Output);var value=old.RootElement;if(value.GetProperty("status").GetString()=="running"&&DateTimeOffset.UtcNow.ToUnixTimeSeconds()-value.GetProperty("updated").GetDouble()<3){status.Text=T("running");return;}}
        var launchedAt=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()/1000.0;
        using var child=Process.Start(Commands.Info("wsl.exe",Commands.WslCommand(distro,root,"launch"),false)) ?? throw new IOException("Cannot start WSL session");status.Text=T("working");
        while(!child.HasExited) {
            await Task.Delay(2000);
            var snapshot=await Commands.Run("wsl.exe",new[]{"-d",distro,"--","cat",root+"/.runtime/desktop-session.json"});
            if(snapshot.Code!=0)continue;
            using var state=JsonDocument.Parse(snapshot.Output);var value=state.RootElement;
            if(value.GetProperty("updated").GetDouble()<launchedAt)continue;
            if(value.GetProperty("status").GetString()=="running"){status.Text=T("running");return;}
            if(value.GetProperty("status").GetString()=="failed")throw new IOException(value.GetProperty("error").GetString());
        }
        if(child.ExitCode!=0)throw new IOException("Desktop session exited with code "+child.ExitCode);
        status.Text=T("ready");
    }
}

static class Program {
    [STAThread] public static int Main(string[] args) {
        if(args.Contains("--self-test")) {
            try {
                Assets.ValidatePayload();
                var ui=JsonSerializer.Deserialize<Dictionary<string,Dictionary<string,string>>>(Assets.Text("ui.json"))!;
                foreach(var lang in new[]{"zh-TW","zh-CN","en","ja"}){if(!ui[lang].ContainsKey("confirm"))throw new Exception("Missing localized consent");if(Assets.Read("INSTALL."+lang+".md").Length==0)throw new Exception("Missing offline installation guide");}
                var parts=Commands.WslCommand("Ubuntu-24.04","/home/user/repo with spaces","launch");
                if(parts[3]!="/home/user/repo with spaces")throw new Exception("Path boundary broken");
                using var zip=new ZipArchive(new MemoryStream(Assets.Read("payload.zip")));
                if(zip.Entries.Any(e=>e.FullName.StartsWith('/')||e.FullName.Split('/').Contains("..")))throw new Exception("Unsafe payload paths");
                if((zip.GetEntry("scripts/setup")!.ExternalAttributes >> 16 & 0x49)==0)throw new Exception("Missing Unix executable bits");
                using(var script=new StreamReader(zip.GetEntry("scripts/setup")!.Open()))if(script.ReadToEnd().Contains('\r'))throw new Exception("Shell script contains Windows newlines");
                if(zip.GetEntry("scripts/desktop.py")==null)throw new Exception("Missing desktop supervisor");
                if(args.Length>1)File.WriteAllText(args[1],"PASS: embedded payload, four languages, WSL arguments and startup verified\n");
                return 0;
            }catch(Exception e){if(args.Length>1)File.WriteAllText(args[1],e.ToString());return 1;}
        }
        var app=new Application();return app.Run(new Launcher());
    }
}
