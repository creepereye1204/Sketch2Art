document.addEventListener("DOMContentLoaded", function () {
  var form = document.querySelector("form");
  var submitButton = document.querySelector("button");
  var imageContainer = document.getElementById("result");
  var progressBarContainer = document.getElementById("progress-bar-container");
  var progressBar = document.getElementById("progress-bar");
  var progressText = document.getElementById("progress-text");
  var fileInputFont = document.getElementById("file-input-font");
  var fileInputBackground = document.getElementById("file-input-background");

  progressBar.style.width = "0%";
  submitButton.addEventListener("click", uploadImage);

  form.addEventListener("input", pickImages);

  function pickImages(event) {
    var fileInput = form.querySelector('input[type="file"]');
    var file = fileInput.files[0];
    if (file) {
      fileInputFont.textContent = `이미지 "${file.name}" 선택됨 (다시 누르면 따른 이미지 찾기)`;
      fileInputBackground.style.backgroundColor = "#1976D2";
    } else {
      fileInputFont.textContent = "이미지 선택 하기 (카메라 or 갤러리)";
      fileInputBackground.style.backgroundColor = "#4CAF50";
    }
  }

  function uploadImage(event) {
    event.preventDefault();
    var socket = io();
    var formData = new FormData(form);

    var fileInput = form.querySelector('input[type="file"]');
    var file = fileInput.files[0];
    if (file) {
      var canvas = document.createElement("canvas");
      var context = canvas.getContext("2d");
      var img = new Image();
      img.src = URL.createObjectURL(file);
      img.onload = function () {
        canvas.width = 1024;
        canvas.height = 1024;
        context.drawImage(img, 0, 0, 1024, 1024);
        canvas.toBlob(function (blob) {
          formData.set("file", blob, file.name);

          if (blob.size > 1024 * 1024) {
            var quality = 0.8;
            do {
              canvas.toBlob(
                function (newBlob) {
                  formData.set("file", newBlob, file.name);
                },
                "image/jpeg",
                quality
              );
              quality -= 0.1;
            } while (newBlob.size > 1024 * 1024);
          }

          socket.emit("upload_image", {
            file: formData.get("file"),
            style: formData.get("style"),
            prompt: formData.get("prompt"),
            negative_prompt: formData.get("negative_prompt"),
          });

          imageContainer.innerHTML =
            '<div class="loading-animation">Loading...</div>';
          progressBarContainer.style.display = "block";
          submitButton.style.backgroundColor = "#1976D2";
          submitButton.textContent = "전송됨";
          submitButton.disabled = true;

          socket.on("datas", function (data) {
            if (data.latents) {
              var imageData = data.latents;
              var img = document.createElement("img");
              img.src = "data:image/png;base64," + imageData;
              imageContainer.innerHTML = "";
              imageContainer.appendChild(img);
              submitButton.style.backgroundColor = "initial";
              submitButton.textContent = "전송";
              submitButton.style.backgroundColor = "#4CAF50";
              submitButton.disabled = false;
            } else {
              imageContainer.innerHTML =
                '<div class="loading-animation">Loading...</div>';
            }

            var step = data.step;
            var timestep = data.timestep;
            var progressPercentage = (step / 25) * 100;
            progressBar.style.width = progressPercentage + "%";
            progressText.textContent = `완성까지 :${
              (step / 25) * 100
            } % , 남은 시간: ${timestep / 100} 초`;
          });
        }, "image/jpeg");
      };
    } else {
      alert("이미지를 선택해주세요.");
    }
  }
});
