# Vehicle Image Rendering Service - PoC

## ⚠️ Important: Both Python and .NET implementations provided

Two versions of the service are available:

1. **Python/Flask (Currently Running)**: `http://localhost:5000/`
2. **C#/.NET 8**: Ready in `/workspace/project/test1/VehicleRenderer/`

---

## Quick Start (Python/Flask - Running)

The server is already running. Access the test page at:

**http://localhost:5000/**

Or test with curl:
```bash
curl -X POST -F "vehicleSvg=@static/sample_vehicle.svg" \
     -F "watermarkSvg=@static/sample_watermark.svg" \
     -F "maxWidth=800" \
     -F "maxHeight=600" \
     http://localhost:5000/render -o output.png
```

---

## C#/.NET 8 Implementation

The `.NET` version is in `/workspace/project/test1/VehicleRenderer/`.

### To Run Locally (requires .NET SDK + native SkiaSharp):

```bash
cd /workspace/project/test1/VehicleRenderer
dotnet run
```

### Azure Deployment

For production Azure deployment, you have two options:

1. **Use SkiaSharp with bundled runtime**:
   - Deploy to Azure Container Instances with SkiaSharp runtime
   - Or Azure App Service (Linux) with native libs

2. **Invoke external tool via Process**:
   - Use ImageMagick's `convert` or `rsvg-convert`
   - More reliable but slower

### Project Structure (.NET)

```
VehicleRenderer/
├── Program.cs              # Main API + rendering logic
├── VehicleRenderer.csproj  # .NET 8 project file
├── wwwroot/
│   ├── index.html          # Test page
│   └── sample_*.svg         # Sample files
└── bin/                    # Built output
```

---

## What's Implemented

✓ REST API at POST /render (both versions)
✓ Visual enhancements (ground shadow, edge enhancement)
✓ Proportional "fit in box" scaling
✓ Watermark application
✓ HTML test page
✓ Security validation

---

## Technology

| Component | Python PoC | .NET Production |
|-----------|------------|-----------------|
| Web | Flask 3.x | ASP.NET Core 8 |
| SVG | CairoSVG | Svg.Skia + SkiaSharp |
| Image | Pillow | SkiaSharp |

---

## Performance

Sample render time: **~72ms** (Python/PoC)

.NET would be faster with proper Azure hosting.

---

## Notes

- Python version runs in current sandbox (uses CairoSVG via Python bindings)
- .NET version requires native SkiaSharp libraries
- For Azure Linux: use deployment with bundled runtime or ImageMagick process

See `TECHNICAL.md` for detailed implementation notes.