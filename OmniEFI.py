import sys, ctypes, os, threading, requests, zipfile, io, plistlib
from pathlib import Path

# --- DATABASE DE RECURSOS ATUALIZADA ---
BASE_LINKS = {
    "OpenCore": "https://github.com/acidanthera/OpenCorePkg/releases/download/1.0.3/OpenCore-1.0.3-RELEASE.zip",
    "Resources": "https://github.com/acidanthera/OcBinaryData/archive/master.zip",
    "HfsPlus": "https://github.com/acidanthera/OcBinaryData/raw/master/Drivers/HfsPlus.efi",
    "Lilu": "https://github.com/acidanthera/Lilu/releases/download/1.7.0/Lilu-1.7.0-RELEASE.zip",
    "VirtualSMC": "https://github.com/acidanthera/VirtualSMC/releases/download/1.3.4/VirtualSMC-1.3.4-RELEASE.zip",
    "WhateverGreen": "https://github.com/acidanthera/WhateverGreen/releases/download/1.6.7/WhateverGreen-1.6.7-RELEASE.zip",
    "AppleALC": "https://github.com/acidanthera/AppleALC/releases/download/1.9.2/AppleALC-1.9.2-RELEASE.zip"
}

def run_as_admin():
    if ctypes.windll.shell32.IsUserAnAdmin(): return True
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{os.path.abspath(sys.argv[0])}"', None, 1)
    return False

if __name__ == "__main__":
    if not run_as_admin(): sys.exit()

    import customtkinter as ctk
    from tkinter import filedialog

    class OmniEFI(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("OmniEFI Builder v4.1")
            self.geometry("650x795")
            
            self.cpu_is_amd = False
            self.net_is_intel = False
            self.active_links = BASE_LINKS.copy()

            self.main = ctk.CTkFrame(self, fg_color="transparent")
            self.main.pack(fill="both", expand=True, padx=30, pady=15)
            
            ctk.CTkLabel(self.main, text="OmniEFI: HARDWARE ENGINE", font=("Roboto", 24, "bold"), text_color="#2ecc71").pack(pady=(0, 10))
            
            self.path_entry = ctk.CTkEntry(self.main, width=550, placeholder_text="Destino (Ex: E:\\ ou C:\\Users\\Luca3muj\\Desktop)")
            self.path_entry.pack(pady=5)
            ctk.CTkButton(self.main, text="Selecionar Pasta/Pendrive", command=self.escolher_pasta, fg_color="#34495e").pack(pady=5)
            
            self.status_label = ctk.CTkLabel(self.main, text="Aguardando Scanner...", font=("Roboto", 13, "bold"), text_color="#3498db")
            self.status_label.pack(pady=(15, 0))
            
            self.progress_frame = ctk.CTkFrame(self.main, fg_color="transparent")
            self.file_name_label = ctk.CTkLabel(self.progress_frame, text="Iniciando...", font=("Roboto", 11, "italic"), text_color="#bdc3c7")
            self.file_name_label.pack(pady=(5, 2))
            
            self.bar_container = ctk.CTkFrame(self.progress_frame, fg_color="transparent")
            self.bar_container.pack()
            self.progress = ctk.CTkProgressBar(self.bar_container, width=550)
            self.progress.set(0); self.progress.pack(side="left", padx=10)
            self.percent_label = ctk.CTkLabel(self.bar_container, text="0%", font=("Roboto", 12, "bold"))
            self.percent_label.pack(side="left")

            self.log_box = ctk.CTkTextbox(self.main, height=450, fg_color="#000", text_color="#00FF00", font=("Consolas", 11))
            self.log_box.pack(fill="x", pady=10)
            
            self.btn_gen = ctk.CTkButton(self.main, text="GERAR EFI COMPLETA", fg_color="#2ecc71", font=("Roboto", 18, "bold"), height=50, command=self.start_thread)
            self.btn_gen.pack(fill="x", pady=10)

            self.after(500, self.full_hardware_scan)

        def log(self, t): self.log_box.insert("end", f"> {t}\n"); self.log_box.see("end")
        def escolher_pasta(self):
            d = filedialog.askdirectory()
            if d: self.path_entry.delete(0, "end"); self.path_entry.insert(0, d)

        def full_hardware_scan(self):
            self.log("--- SCANNER DE HARDWARE ---")
            try:
                import wmi
                c = wmi.WMI()
                for cpu in c.Win32_Processor():
                    self.log(f"CPU: {cpu.Name.strip()}"); self.cpu_is_amd = "AMD" in cpu.Name.upper()
                for gpu in c.Win32_VideoController(): self.log(f"GPU: {gpu.Name}")
                ram = sum(int(m.Capacity) for m in c.Win32_PhysicalMemory()) // (1024**3)
                self.log(f"MEMÓRIA: {ram}GB RAM")
                for d in c.Win32_DiskDrive():
                    size = int(d.Size)//(1024**3) if d.Size else 0
                    self.log(f"DISCO: {d.Caption} ({size}GB)")
                for net in c.Win32_NetworkAdapter(PhysicalAdapter=True):
                    if net.NetEnabled:
                        self.log(f"REDE: {net.Name}")
                        if "INTEL" in net.Name.upper(): self.net_is_intel = True
                self.ajustar_links()
                self.status_label.configure(text="HARDWARE MAPEADO!", text_color="#2ecc71")
            except Exception as e: self.log(f"Erro no Scanner: {e}")

        def ajustar_links(self):
            if self.cpu_is_amd:
                self.active_links["CpuKext"] = "https://github.com/trulyspinach/SMCAMDProcessor/releases/download/0.7.5/SMCAMDProcessor.zip"
                self.active_links["SSDT"] = "https://github.com/dortania/Getting-Started-With-ACPI/raw/master/extra-files/compiled/SSDT-EC-USBX-DESKTOP.aml"
            else:
                self.active_links["CpuKext"] = "https://github.com/acidanthera/VirtualSMC/releases/download/1.3.4/VirtualSMC-1.3.4-RELEASE.zip"
                self.active_links["SSDT"] = "https://github.com/dortania/Getting-Started-With-ACPI/raw/master/extra-files/compiled/SSDT-PLUG-DRTNIA.aml"
            # Link da Realtek fixo para a versão estável
            self.active_links["Network"] = "https://github.com/acidanthera/IntelMausi/releases/download/1.0.8/IntelMausi-1.0.8-RELEASE.zip" if self.net_is_intel else "https://github.com/Mieze/RTL8111_driver_for_OS_X/releases/download/2.4.2/RealtekRTL8111-V2.4.2.zip"

        def download_with_progress(self, url, name):
            self.file_name_label.configure(text=f"Baixando: {name}...")
            self.log(f"Baixando {name}...")
            try:
                response = requests.get(url, stream=True, timeout=25)
                total_size = int(response.headers.get('content-length', 0))
                buffer = io.BytesIO()
                downloaded = 0
                for data in response.iter_content(chunk_size=8192):
                    downloaded += len(data)
                    buffer.write(data)
                    if total_size > 0:
                        p = downloaded / total_size
                        self.progress.set(p); self.percent_label.configure(text=f"{int(p * 100)}%")
                        self.update_idletasks()
                return buffer.getvalue()
            except: return None

        def create_config_plist(self, oc_path):
            smbios = "iMacPro1,1" if self.cpu_is_amd else "iMac19,1"
            config = {
                "ACPI": {"Add": [{"Path": self.active_links["SSDT"].split('/')[-1], "Enabled": True}]},
                "Kernel": {
                    "Add": [
                        {"BundlePath": "Lilu.kext", "Enabled": True, "ExecutablePath": "Contents/MacOS/Lilu", "PlistPath": "Contents/Info.plist"},
                        {"BundlePath": "VirtualSMC.kext", "Enabled": True, "ExecutablePath": "Contents/MacOS/VirtualSMC", "PlistPath": "Contents/Info.plist"},
                        {"BundlePath": "WhateverGreen.kext", "Enabled": True, "ExecutablePath": "Contents/MacOS/WhateverGreen", "PlistPath": "Contents/Info.plist"},
                        {"BundlePath": "AppleALC.kext", "Enabled": True, "ExecutablePath": "Contents/MacOS/AppleALC", "PlistPath": "Contents/Info.plist"}
                    ],
                    "Quirks": {"ProvideCurrentCpuInfo": self.cpu_is_amd, "PanicNoKextDump": True, "XhciPortLimit": True}
                },
                "Misc": {
                    "Boot": {"PickerMode": "External", "PickerAttributes": 17, "ShowPicker": True, "Timeout": 5},
                    "Security": {"AllowSetDefault": True, "ScanPolicy": 0, "SecureBootModel": "Disabled", "Vault": "Optional"}
                },
                "NVRAM": {"Add": {"7C436110-AB2A-4BBB-A880-FE41995C9F82": {"boot-args": "-v debug=0x100 alcid=1", "prev-lang:kbd": "pt-BR:128"}}},
                "PlatformInfo": {"Generic": {"SystemProductName": smbios, "AdviseFeatures": True}},
                "UEFI": {"Drivers": [{"Enabled": True, "Path": "HfsPlus.efi"}, {"Enabled": True, "Path": "OpenRuntime.efi"}, {"Enabled": True, "Path": "OpenCanopy.efi"}]}
            }
            with open(oc_path / "config.plist", "wb") as f: plistlib.dump(config, f)

        def start_thread(self):
            if not self.path_entry.get(): return
            threading.Thread(target=self.generate, daemon=True).start()

        def generate(self):
            self.btn_gen.configure(state="disabled"); self.progress_frame.pack(pady=10)
            dest = Path(self.path_entry.get()) / "EFI"; oc = dest / "OC"
            try:
                for p in ["ACPI", "Drivers", "Kexts", "Resources", "Tools"]: (oc/p).mkdir(parents=True, exist_ok=True)
                (dest/"BOOT").mkdir(parents=True, exist_ok=True)

                for key, url in self.active_links.items():
                    if url.endswith(".zip"):
                        data = self.download_with_progress(url, key)
                        if data:
                            try:
                                with zipfile.ZipFile(io.BytesIO(data)) as z:
                                    if key == "OpenCore":
                                        with open(dest/"BOOT/BOOTx64.efi", "wb") as f: f.write(z.read('X64/EFI/BOOT/BOOTx64.efi'))
                                        with open(oc/"OpenCore.efi", "wb") as f: f.write(z.read('X64/EFI/OC/OpenCore.efi'))
                                        for n in z.namelist():
                                            if 'X64/EFI/OC/Drivers/' in n and n.endswith('.efi'):
                                                with open(oc/"Drivers"/n.split('/')[-1], "wb") as f: f.write(z.read(n))
                                    elif key == "Resources":
                                        for f in z.namelist():
                                            if "/Resources/" in f and not f.endswith("/"):
                                                target = oc / "Resources" / f.split("/Resources/")[1]
                                                target.parent.mkdir(parents=True, exist_ok=True)
                                                with open(target, "wb") as t: t.write(z.read(f))
                                    else: # KEXTS
                                        for name in z.namelist():
                                            if ".kext/" in name and not name.endswith("/"):
                                                k_name = name.split(".kext/")[0].split("/")[-1] + ".kext"
                                                target = oc / "Kexts" / k_name / name.split(".kext/")[1]
                                                target.parent.mkdir(parents=True, exist_ok=True)
                                                with open(target, "wb") as t: t.write(z.read(name))
                            except zipfile.BadZipFile: self.log(f"Aviso: O arquivo {key} não é um Zip válido. Ignorado.")

                # Baixa o HfsPlus e o SSDT (que não são zips)
                with open(oc/"Drivers/HfsPlus.efi", "wb") as f: f.write(requests.get(self.active_links["HfsPlus"]).content)
                with open(oc/f"ACPI/{self.active_links['SSDT'].split('/')[-1]}", "wb") as f: f.write(requests.get(self.active_links["SSDT"]).content)

                self.create_config_plist(oc)
                self.log("--- EFI GERADA COM SUCESSO! ---")
                self.status_label.configure(text="TUDO PRONTO!", text_color="#2ecc71")
            except Exception as e: self.log(f"Erro: {e}")
            self.progress_frame.pack_forget(); self.btn_gen.configure(state="normal")

    app = OmniEFI(); app.mainloop()
