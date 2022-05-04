import nls
import base64
import threading
import configure


class Result:
    def __init__(self, text: str):
        self.mp3 = ""
        self.success = None
        self.txt = text
        self.byte = b""


# 以下代码会根据上述TEXT文本反复进行语音合成
class AliyunTls:
    class Tls:
        def __init__(self, url: str, key: str, secret: str, app: str, res: "Result", **kwargs):
            self.__res = res
            self.__kwargs = kwargs
            self.__th = threading.Thread(target=self.__test_run)
            self.url = url
            self.key = key
            self.secret = secret
            self.app = app

        def start(self):
            self.__th.start()
            self.__th.join()
            if self.__res.success is None:
                self.__res.mp3 = base64.b64encode(self.__res.byte).decode("ascii")
                self.__res.success = True
            return self.__res

        def on_error(self, message, *args):
            self.__res.success = False

        def data_to_base64(self, data, *_):
            try:
                self.__res.byte += data
            except Exception:
                self.__res.success = False

        def __test_run(self):
            tts = nls.NlsSpeechSynthesizer(
                url=self.url,
                akid=self.key,
                aksecret=self.secret,
                appkey=self.app,
                on_data=self.data_to_base64,
                on_error=self.on_error,
            )

            tts.start(self.__res.txt, aformat="mp3", wait_complete=True, **self.__kwargs)

    def __init__(self, url: str, key: str, secret: str, app: str):
        self.url = url
        self.key = key
        self.secret = secret
        self.app = app
        self.kwargs = {
            "voice": "Luca",
            "speech_rate": -500,
        }

    def start(self, text: str):
        return AliyunTls.Tls(self.url, self.key, self.secret, self.app, Result(text), **self.kwargs).start()


if len(configure.conf["ALIYUN_KEY"]) == 0:
    print("Not aliyun key")
    exit(1)

tls = AliyunTls(configure.conf["TLS_URL"], configure.conf["ALIYUN_KEY"],
                configure.conf["ALIYUN_SECRET"], configure.conf["TLS_APPID"])
