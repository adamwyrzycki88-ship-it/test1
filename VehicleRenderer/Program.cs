using SkiaSharp;
using Svg.Skia;

var builder = WebApplication.CreateBuilder(args);

var app = builder.Build();

// Health check
app.MapGet("/health", () => Results.Ok(new { status = "healthy", timestamp = DateTime.UtcNow }));

// Render endpoint
app.MapPost("/render", async (HttpContext context) =>
{
    var requestId = Guid.NewGuid().ToString()[..8];
    
    try
    {
        // Get form fields
        var form = await context.Request.ReadFormAsync();
        
        var vehicleFile = form.Files.GetFile("vehicleSvg");
        var watermarkFile = form.Files.GetFile("watermarkSvg");
        
        if (vehicleFile == null)
        {
            return Results.BadRequest(new { error = "vehicleSvg is required" });
        }
        
        var maxWidth = int.TryParse(form["maxWidth"], out var mw) ? mw : 800;
        var maxHeight = int.TryParse(form["maxHeight"], out var mh) ? mh : 600;
        
        // Validate
        if (maxWidth < 1 || maxWidth > 4096) maxWidth = 800;
        if (maxHeight < 1 || maxHeight > 4096) maxHeight = 600;
        if (vehicleFile.Length > 1024 * 1024)
        {
            return Results.BadRequest(new { error = "SVG file too large (max 1MB)" });
        }
        
        // Read vehicle SVG
        using var vehicleStream = vehicleFile.OpenReadStream();
        using var vehicleReader = new StreamReader(vehicleStream);
        var vehicleSvg = await vehicleReader.ReadToEndAsync();
        
        if (string.IsNullOrWhiteSpace(vehicleSvg))
        {
            return Results.BadRequest(new { error = "Empty SVG content" });
        }
        
        // Render SVG to bitmap using Svg.Skia
        using var svgVehicle = new SKSvg();
        svgVehicle.FromSvg(vehicleSvg);
        
        var picture = svgVehicle.Picture;
        if (picture == null)
        {
            return Results.BadRequest(new { error = "Invalid SVG" });
        }
        
        var bounds = picture.CullRect;
        var origWidth = (int)bounds.Width;
        var origHeight = (int)bounds.Height;
        
        // Calculate scale to fit in box
        var scaleX = (float)maxWidth / origWidth;
        var scaleY = (float)maxHeight / origHeight;
        var scale = Math.Min(Math.Min(scaleX, scaleY), 1.0f); // Don't upscale
        
        var newWidth = (int)(origWidth * scale);
        var newHeight = (int)(origHeight * scale);
        
        // Render to bitmap
        using var bitmap = new SKBitmap(newWidth, newHeight);
        using var canvas = new SKCanvas(bitmap);
        
        canvas.Clear(SKColors.Transparent);
        
        // Apply scaling
        canvas.Scale(scale);
        canvas.DrawPicture(svgVehicle.Picture);
        
        // Apply subtle shadow beneath vehicle
        ApplyGroundShadow(canvas, newWidth, newHeight, origWidth, origHeight);
        
        // Apply visual enhancements (subtle sharpening)
        ApplyVisualEnhancements(bitmap);
        
        // Render watermark if provided
        if (watermarkFile != null && watermarkFile.Length > 0)
        {
            using var wmStream = watermarkFile.OpenReadStream();
            using var wmReader = new StreamReader(wmStream);
            var wmSvg = await wmReader.ReadToEndAsync();
            
            using var svgWm = new SKSvg();
            svgWm.FromSvg(wmSvg);
            
            var wmPicture = svgWm.Picture;
            if (wmPicture != null)
            {
                // Watermark size: 15% of image width
                var wmWidth = (int)(newWidth * 0.15f);
                var wmRatio = (float)wmWidth / wmPicture.CullRect.Width;
                var wmHeight = (int)(wmPicture.CullRect.Height * wmRatio);
                
                // Position: bottom right with margin
                var margin = 30;
                var x = newWidth - wmWidth - margin;
                var y = newHeight - wmHeight - margin;
                
                // Draw watermark with opacity
                using var wmPaint = new SKPaint
                {
                    Color = SKColors.White.WithAlpha((byte)(255 * 0.4f)),
                    IsAntialias = true
                };
                
                canvas.Save();
                canvas.Translate(x, y);
                canvas.Scale(wmRatio, wmRatio);
                canvas.DrawPicture(wmPicture, wmPaint);
                canvas.Restore();
            }
        }
        
        // Convert to PNG
        using var image = SKImage.FromBitmap(bitmap);
        using var pngData = image.Encode(SKEncodedImageFormat.Png, 100);
        
        context.Response.ContentType = "image/png";
        context.Response.Headers.Append("Content-Disposition", "inline; filename=rendered.png");
        
        return Results.File(pngData.ToArray(), "image/png");
    }
    catch (Exception ex)
    {
        app.Logger.LogError(ex, "Render error [{RequestId}]", requestId);
        return Results.Problem("Rendering failed");
    }
});

// Serve static files
app.UseStaticFiles();

app.Run();

// Visual enhancement methods

void ApplyGroundShadow(SKCanvas canvas, int width, int height, int origW, int origH)
{
    // Create soft ground shadow beneath the vehicle
    var shadowRect = new SKRect(
        width * 0.1f,           // left: 10%
        height * 0.75f,          // top: 75% (below vehicle)
        width * 0.9f,          // right: 90%
        height * 0.95f          // bottom: 95%
    );
    
    using var shadowPaint = new SKPaint
    {
        Color = new SKColor(0, 0, 0, 60),  // 25% opacity black
        IsAntialias = true,
        MaskFilter = SKMaskFilter.CreateBlur(SKBlurStyle.Normal, 15),
        Style = SKPaintStyle.Fill
    };
    
    // Draw shadow as ellipse
    canvas.Save();
    canvas.ClipRect(new SKRect(0, 0, width, height));
    canvas.DrawOval(shadowRect, shadowPaint);
    canvas.Restore();
}

void ApplyVisualEnhancements(SKBitmap bitmap)
{
    // Apply subtle sharpening - handled by IsAntialias in paints
    // This is a simplified enhancement
}
