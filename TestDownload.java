import java.io.*;
import java.net.*;

public class TestDownload {
    public static void main(String[] args) {
        String url = "https://github.com/VrumBurrinho/Raven/releases/download/release/python-embed.zip";
        try {
            HttpURLConnection hc = _open(url);
            if (hc == null) {
                System.out.println("hc is null");
                return;
            }
            System.out.println("Response code: " + hc.getResponseCode());
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
    private static HttpURLConnection _open(String url) throws Exception {
        for (int r = 0; r < 5; r++) {
            HttpURLConnection hc = (HttpURLConnection) new URI(url).toURL().openConnection();
            hc.setInstanceFollowRedirects(false);
            hc.setConnectTimeout(15000);
            hc.setReadTimeout(30000);
            hc.setRequestProperty("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)");
            int s = hc.getResponseCode();
            if (s == 301 || s == 302 || s == 303 || s == 307 || s == 308) {
                url = hc.getHeaderField("Location");
                hc.disconnect();
                continue;
            }
            return hc;
        }
        return null;
    }
}
