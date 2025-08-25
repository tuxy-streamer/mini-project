const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const responseBox = document.getElementById("responseBox");

navigator.mediaDevices
  .getUserMedia({ video: true })
  .then((stream) => (video.srcObject = stream))
  .catch((err) =>
    alert("Camera access denied or not available: " + err.message),
  );

function generateUserId() {
  return Math.floor(Math.random() * 65536) - 32768;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function captureImagesToMemory(numImages = 20) {
  const context = canvas.getContext("2d");
  const images = [];
  for (let i = 0; i < numImages; i++) {
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) =>
      canvas.toBlob(resolve, "image/jpeg"),
    );
    images.push(blob);
    await delay(10);
  }
  return images;
}

async function uploadImages(endpoint, images, userId) {
  const formData = new FormData();
  formData.append("user_id", userId);
  images.forEach((blob, i) => {
    formData.append("images", blob, `capture_${i + 1}.jpg`);
  });
  const res = await fetch(endpoint, {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  responseBox.style.display = "block";
  responseBox.textContent = JSON.stringify(data, null, 2);
}

async function startCaptureAndUpload() {
  const userId = generateUserId();
  const endpoint = "http://localhost:3000/register";
  const images = await captureImagesToMemory(100);
  await uploadImages(endpoint, images, userId);
}
