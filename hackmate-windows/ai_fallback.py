import urllib.request
import urllib.error
import json
from pathlib import Path
from hardware import HardwareProfile


def _load_key() -> str:
    env_file = Path(__file__).parent / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip()
    import os
    return os.environ.get("GROQ_API_KEY", "")


def ask_groq(profile: HardwareProfile, unknown_devices: list[str]) -> str:
    key = _load_key()
    if not key:
        return ""

    prompt = f"""You are a hackintosh expert. A user is building an OpenCore EFI and needs kext recommendations for unrecognized hardware.

Hardware profile:
- CPU: {profile.cpu_name} (Gen {profile.cpu_generation}, {profile.cpu_codename})
- GPU: {profile.gpu_name} [{profile.gpu_vendor}]
- Audio: {profile.audio_codec}
- Ethernet: {profile.ethernet_name}
- WiFi: {profile.wifi_name}
- Platform: {profile.platform}
- SMBIOS: {profile.smbios_model}

Unrecognized devices that need kexts:
{chr(10).join(f'- {d}' for d in unknown_devices)}

For each unrecognized device, respond with ONLY a JSON array of objects like this:
[
  {{
    "device": "device name",
    "kext": "KextName",
    "repo": "github-owner/repo",
    "note": "why this kext"
  }}
]

Only include kexts that are real, publicly available on GitHub, and work with OpenCore. If a device is unsupported on macOS, say so in the note and set kext to null."""

    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 512,
    }).encode()

    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": "HackMate/1.0",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"ERROR: {e}"


def parse_groq_response(response: str) -> list[dict]:
    try:
        start = response.find("[")
        end = response.rfind("]") + 1
        if start == -1 or end == 0:
            return []
        return json.loads(response[start:end])
    except Exception:
        return []


if __name__ == "__main__":
    from hardware import scan
    profile = scan()
    test_devices = ["Realtek RTS5227 Card Reader", "Intel Thunderbolt 3 NHI"]
    print(f"Asking Groq about: {test_devices}")
    resp = ask_groq(profile, test_devices)
    print(f"\nGroq response:\n{resp}")
    parsed = parse_groq_response(resp)
    print(f"\nParsed: {parsed}")
