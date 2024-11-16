import cv2 as cv
import numpy as np
import winsound
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QComboBox, QLabel, QFileDialog
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl


class VisionAgent(QMainWindow):
    def __init__(self):
        super().__init__()
        self.urlWindow = MainWindow()

        self.setWindowTitle("파노라마 영상")
        self.setGeometry(200, 200, 700, 200)

        collectButton = QPushButton("영상 수집", self)
        self.showButton = QPushButton("영상 보기", self)
        self.stitchButton = QPushButton("봉합", self)
        self.saveButton = QPushButton("저장", self)
        quitButton = QPushButton("나가기", self)
        urlButton = QPushButton("추가 기능", self)
        self.label = QLabel("환영합니다!", self)

        self.effectCombo = QComboBox(self)
        self.effectCombo.addItems(
            ["원본", "엠보싱", "카툰", "연필 스케치(명암)", "연필 스케치(컬러)", "유화"]
        )

        collectButton.setGeometry(10, 25, 100, 30)
        self.effectCombo.setGeometry(120, 25, 150, 30)
        self.showButton.setGeometry(280, 25, 100, 30)
        self.stitchButton.setGeometry(390, 25, 100, 30)
        self.saveButton.setGeometry(490, 25, 100, 30)
        quitButton.setGeometry(590, 25, 100, 30)
        urlButton.setGeometry(10, 60, 100, 30)
        self.label.setGeometry(10, 100, 600, 170)

        self.showButton.setEnabled(False)
        self.stitchButton.setEnabled(False)
        self.saveButton.setEnabled(False)

        collectButton.clicked.connect(self.collectFunction)
        self.showButton.clicked.connect(self.showFunction)
        self.stitchButton.clicked.connect(self.stitchFunction)
        self.saveButton.clicked.connect(self.saveFunction)
        quitButton.clicked.connect(self.quitFunction)
        urlButton.clicked.connect(self.openUrlWindow)

    def openUrlWindow(self):
        self.urlWindow.show()

    def collectFunction(self):
        self.showButton.setEnabled(False)
        self.stitchButton.setEnabled(False)
        self.saveButton.setEnabled(False)
        self.label.setText("c를 여러 번 눌러 수집하고 끝나면 q를 눌러 비디오를 끕니다.")

        self.cap = cv.VideoCapture(0, cv.CAP_DSHOW)
        if not self.cap.isOpened():
            sys.exit("카메라 연결 실패")

        self.imgs = []
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break

            pick_effect = self.effectCombo.currentIndex()
            if pick_effect == 0:
                special_img = frame
            elif pick_effect == 1:
                femboss = np.array([[-1.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
                gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
                gray16 = np.int16(gray)
                special_img = np.uint8(np.clip(cv.filter2D(gray16, -1, femboss) + 128, 0, 255))
            elif pick_effect == 2:
                special_img = cv.stylization(frame, sigma_s=60, sigma_r=0.45)
            elif pick_effect == 3:
                special_img, _ = cv.pencilSketch(frame, sigma_s=60, sigma_r=0.07, shade_factor=0.02)
            elif pick_effect == 4:
                _, special_img = cv.pencilSketch(frame, sigma_s=60, sigma_r=0.07, shade_factor=0.02)
            else:
                special_img = cv.xphoto.oilPainting(frame, 10, 1, cv.COLOR_BGR2Lab)

            cv.imshow("video display", special_img)

            key = cv.waitKey(1)
            if key == ord("c"):
                self.imgs.append(special_img)
            elif key == ord("q"):
                self.cap.release()
                cv.destroyWindow("video display")
                break

        if len(self.imgs) >= 2:
            self.showButton.setEnabled(True)
            self.stitchButton.setEnabled(True)
            self.saveButton.setEnabled(True)

    def showFunction(self):
        self.label.setText("수집된 영상은 " + str(len(self.imgs)) + "장 입니다.")
        stack = cv.resize(self.imgs[0], dsize=(0, 0), fx=0.25, fy=0.25)
        for i in range(1, len(self.imgs)):
            stack = np.hstack((stack, cv.resize(self.imgs[i], dsize=(0, 0), fx=0.25, fy=0.25)))
        cv.imshow("Image collection", stack)

    def stitchFunction(self):
        stitcher = cv.Stitcher.create()
        try:
            status, self.img_stitched = stitcher.stitch(self.imgs)
            if status == cv.Stitcher_OK:
                cv.imshow("Stitched Image", self.img_stitched)
                self.label.setText("봉합 성공!")
            else:
                raise Exception("봉합 실패!")
        except Exception as e:
            winsound.Beep(3000, 500)
            self.label.setText(f"저장 실패 : {str(e)}")

    def saveFunction(self):
        fname, _ = QFileDialog.getSaveFileName(self, "파일 저장", "./")
        if fname:
            cv.imwrite(fname, self.img_stitched)

    def quitFunction(self):
        if hasattr(self, "cap"):
            self.cap.release()
        cv.destroyAllWindows()
        self.close()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.browser = QWebEngineView()

        self.browser.setUrl(QUrl("http://210.94.252.178:20004"))

        self.setCentralWidget(self.browser)

        self.setWindowTitle("추가 기능")
        self.resize(800, 600)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = VisionAgent()
    win.show()
    sys.exit(app.exec())
