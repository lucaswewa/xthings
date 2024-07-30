from pypylon import pylon

camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
camera.Open()

numberOfImagesToGrab = 10
pixelFormat = camera.PixelFormat.Value
print(pixelFormat)

camera.PixelFormat.Value = "Mono8"

camera.StartGrabbingMax(numberOfImagesToGrab)

while camera.IsGrabbing():
    grabResult = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)

    if grabResult.GrabSucceeded():
        print("Size X: ", grabResult.Width)
        print("Size Y: ", grabResult.Height)
        image = grabResult.Array
        print("Gray value of first pixel: ", image[0, 0])

    grabResult.Release()

camera.PixelFormat.Value = pixelFormat

camera.Close()
