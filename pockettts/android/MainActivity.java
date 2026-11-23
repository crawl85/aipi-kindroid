package org.aipi.pocketbridge;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Intent;
import android.os.Bundle;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.util.UUID;

public class MainActivity extends Activity {
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(32, 32, 32, 32);
        TextView title = new TextView(this);
        title.setText("AiPi PocketTTS Bridge");
        title.setTextSize(24);
        layout.addView(title);
        TextView help = new TextView(this);
        help.setText("Select and save your voice in PocketTTS. Start the bridge, then copy its pairing key into the Termux setup prompt.");
        layout.addView(help);
        Button start = new Button(this);
        start.setText("Start bridge");
        start.setOnClickListener(v -> startForegroundService(new Intent(this, SpeechService.class)));
        layout.addView(start);
        Button copy = new Button(this);
        copy.setText("Copy pairing key");
        copy.setOnClickListener(v -> getSystemService(ClipboardManager.class).setPrimaryClip(
            ClipData.newPlainText("AiPi bridge pairing key", key(this))));
        layout.addView(copy);
        Button stop = new Button(this);
        stop.setText("Stop bridge");
        stop.setOnClickListener(v -> stopService(new Intent(this, SpeechService.class)));
        layout.addView(stop);
        setContentView(layout);
    }

    static synchronized String key(android.content.Context context) {
        android.content.SharedPreferences prefs = context.getSharedPreferences("bridge", MODE_PRIVATE);
        String key = prefs.getString("key", null);
        if (key == null) {
            key = UUID.randomUUID().toString();
            prefs.edit().putString("key", key).apply();
        }
        return key;
    }
}
