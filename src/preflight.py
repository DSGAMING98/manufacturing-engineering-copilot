"""Run BEFORE downloading any model. Checks CUDA and available VRAM."""
import sys
import platform


def main():
    try:
        import torch
    except ImportError:
        print("ERROR: PyTorch not installed. Use the README's installation steps.")
        return 1
    print("Python:", sys.version.split()[0], "| OS:", platform.system())
    print("PyTorch:", torch.__version__, "| built CUDA:", torch.version.cuda)
    if not torch.cuda.is_available():
        print("ERROR: torch.cuda.is_available() is False. Training not started.")
        return 1
    props = torch.cuda.get_device_properties(0)
    free, total = torch.cuda.mem_get_info(0)
    print("GPU:", props.name)
    print(f"GPU total: {total / 2**30:.2f} GiB | available: {free / 2**30:.2f} GiB")
    if free < 4.0 * 2**30:
        print("WARNING: free VRAM is limited; close GPU-heavy applications before training.")
    print("PASS: CUDA tensor:", (torch.ones(2, device="cuda") + 1).tolist())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
