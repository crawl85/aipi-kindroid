package org.aipi.pocketbridge;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.os.Bundle;
import android.os.IBinder;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import fi.iki.elonen.NanoHTTPD;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.UUID;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public class SpeechService extends Service {
    private static final String ENGINE = "org.pockettts.android.engine";
    private volatile boolean ready;
    private TextToSpeech tts;
    private Bridge bridge;

    @Override public void onCreate() {
        super.onCreate();
        getSystemService(NotificationManager.class).createNotificationChannel(
            new NotificationChannel("bridge", "AiPi voice bridge", NotificationManager.IMPORTANCE_LOW));
        startForeground(1, notification("Starting PocketTTS"));
        tts = new TextToSpeech(this, status -> {
            ready = status == TextToSpeech.SUCCESS && ENGINE.equals(tts.getDefaultEngine());
            getSystemService(NotificationManager.class).notify(1, notification(
                ready ? "Ready on this phone" : "PocketTTS engine unavailable"));
        }, ENGINE);
        bridge = new Bridge(MainActivity.key(this));
        try {
            bridge.start(5000, false);
        } catch (IOException e) {
            getSystemService(NotificationManager.class).notify(1, notification("Could not open port 8765"));
        }
    }

    private Notification notification(String message) {
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class),
            PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, "bridge").setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("AiPi PocketTTS Bridge").setContentText(message).setContentIntent(open).build();
    }

    @Override public IBinder onBind(Intent intent) { return null; }

    @Override public void onDestroy() {
        ready = false;
        if (bridge != null) bridge.stop();
        if (tts != null) tts.shutdown();
        super.onDestroy();
    }

    private synchronized byte[] synthesize(String text) throws IOException, InterruptedException {
        File file = File.createTempFile("speech-", ".wav", getCacheDir());
        String id = UUID.randomUUID().toString();
        CountDownLatch done = new CountDownLatch(1);
        boolean[] success = {false};
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            @Override public void onStart(String utterance) {}
            @Override public void onDone(String utterance) {
                if (id.equals(utterance)) {
                    success[0] = true;
                    done.countDown();
                }
            }
            @Override public void onError(String utterance) {
                if (id.equals(utterance)) done.countDown();
            }
        });
        try {
            int result = tts.synthesizeToFile(text, new Bundle(), file, id);
            if (result != TextToSpeech.SUCCESS) throw new IOException("Synthesis rejected");
            if (!done.await(20, TimeUnit.SECONDS)) {
                tts.stop();
                throw new IOException("Synthesis timed out");
            }
            if (!success[0] || file.length() < 44 || file.length() > 8000000) {
                throw new IOException("Invalid audio");
            }
            return Files.readAllBytes(file.toPath());
        } finally {
            file.delete();
        }
    }

    private class Bridge extends NanoHTTPD {
        private final byte[] authorization;
        Bridge(String key) {
            super("127.0.0.1", 8765);
            authorization = ("Bearer " + key).getBytes(StandardCharsets.UTF_8);
        }

        @Override public Response serve(IHTTPSession request) {
            if (request.getMethod() != Method.POST || !"/speech".equals(request.getUri())) {
                return error(Response.Status.NOT_FOUND);
            }
            String header = request.getHeaders().get("authorization");
            if (header == null || !MessageDigest.isEqual(authorization, header.getBytes(StandardCharsets.UTF_8))) {
                return error(Response.Status.UNAUTHORIZED);
            }
            if (!ready) return error(Response.Status.SERVICE_UNAVAILABLE);
            try {
                int length = Integer.parseInt(request.getHeaders().get("content-length"));
                if (length < 1 || length > 16000) return error(Response.Status.BAD_REQUEST);
                byte[] body = new byte[length];
                new java.io.DataInputStream(request.getInputStream()).readFully(body);
                String text = new String(body, StandardCharsets.UTF_8).trim();
                if (text.isEmpty() || text.length() > TextToSpeech.getMaxSpeechInputLength()) {
                    return error(Response.Status.BAD_REQUEST);
                }
                byte[] wav = synthesize(text);
                return newFixedLengthResponse(Response.Status.OK, "audio/wav",
                    new ByteArrayInputStream(wav), wav.length);
            } catch (NumberFormatException e) {
                return error(Response.Status.BAD_REQUEST);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return error(Response.Status.SERVICE_UNAVAILABLE);
            } catch (IOException e) {
                return error(Response.Status.SERVICE_UNAVAILABLE);
            }
        }

        private Response error(Response.Status status) {
            return newFixedLengthResponse(status, "text/plain", status.getDescription());
        }
    }
}
