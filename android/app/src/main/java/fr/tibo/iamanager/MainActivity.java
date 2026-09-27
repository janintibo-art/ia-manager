package fr.tibo.iamanager;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.text.InputType;
import android.view.View;
import android.widget.*;
import org.json.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Native companion. No remote WebView, no execution of model output. */
public class MainActivity extends Activity {
    private static final int BG = Color.rgb(16,23,39), CARD = Color.rgb(28,39,59);
    private static final int INK = Color.rgb(234,241,252), ACCENT = Color.rgb(99,221,208);
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private EditText address, code, prompt;
    private Button connect, send, stop, reset, configure, reconnect;
    private LinearLayout connectionPanel;
    private Spinner models;
    private TextView status, reply;
    private LinearLayout messages;
    private ScrollView scroll;
    private final ArrayList<String> refs = new ArrayList<>();
    private JSONArray history = new JSONArray();
    private volatile HttpURLConnection activeConnection;
    private volatile boolean cancelled, destroyed;
    private volatile String requestId = "";
    private boolean busy, connected;
    private String base = "", secret = "";

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16),dp(10),dp(16),dp(8));
        root.setBackgroundColor(BG);
        root.setOnApplyWindowInsetsListener((view, insets) -> {
            view.setPadding(dp(16)+insets.getSystemWindowInsetLeft(), dp(10)+insets.getSystemWindowInsetTop(),
                dp(16)+insets.getSystemWindowInsetRight(), dp(8)+insets.getSystemWindowInsetBottom());
            return insets;
        });
        setContentView(root);
        TextView title = text("IA Manager", 26);
        title.setTypeface(null, Typeface.BOLD);
        root.addView(title);
        root.addView(text("MOBILE  /  VOS MODÈLES SUR LE PC", 11));
        configure = button("Connexion au PC · modifier");
        configure.setVisibility(View.GONE);
        root.addView(configure);
        connectionPanel = new LinearLayout(this);
        connectionPanel.setOrientation(LinearLayout.VERTICAL);
        root.addView(connectionPanel);
        configure.setOnClickListener(v -> {
            connectionPanel.setVisibility(View.VISIBLE); configure.setVisibility(View.GONE);
            connected=false; controls();
        });
        reconnect = button("↻ Reconnecter au PC");
        reconnect.setVisibility(View.GONE);
        root.addView(reconnect);
        reconnect.setOnClickListener(v -> connect());
        address = input("Adresse locale ou HTTPS Tailscale du PC", false);
        address.setSingleLine(true);
        address.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        address.setText(getPreferences(MODE_PRIVATE).getString("address", ""));
        connectionPanel.addView(address);
        code = input("Code affiché dans l’onglet Téléphone du PC", true);
        code.setSingleLine(true);
        code.setSaveEnabled(false);
        connectionPanel.addView(code);
        connect = button("Connecter / actualiser les modèles");
        connectionPanel.addView(connect);
        connect.setOnClickListener(v -> connect());
        models = new Spinner(this);
        root.addView(models);
        status = text("Même réseau ou accès Tailscale · démarrez le serveur sur le PC.", 12);
        root.addView(status);
        scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        messages = new LinearLayout(this);
        messages.setOrientation(LinearLayout.VERTICAL);
        scroll.addView(messages);
        root.addView(scroll, new LinearLayout.LayoutParams(-1,0,1));
        prompt = input("Votre message…", false);
        prompt.setMinLines(2);
        prompt.setMaxLines(4);
        root.addView(prompt);
        LinearLayout actions = new LinearLayout(this);
        send = button("Envoyer"); stop = button("Arrêter"); reset = button("Nouveau");
        for (Button b : new Button[]{send,stop,reset}) actions.addView(b,new LinearLayout.LayoutParams(0,-2,1));
        root.addView(actions);
        send.setOnClickListener(v -> send());
        stop.setOnClickListener(v -> cancelRequest());
        reset.setOnClickListener(v -> new AlertDialog.Builder(this).setTitle("Nouveau chat")
            .setMessage("Effacer la conversation enregistrée sur ce téléphone ?")
            .setNegativeButton("Garder", null).setPositiveButton("Effacer", (d,w) -> {
                history = new JSONArray(); saveHistory(); renderHistory();
            }).show());
        loadHistory(); renderHistory(); controls();
    }

    private int dp(int n) { return (int)(getResources().getDisplayMetrics().density*n); }
    private TextView text(String value, int size) {
        TextView v = new TextView(this); v.setText(value); v.setTextColor(INK); v.setTextSize(size);
        v.setPadding(dp(4),dp(5),dp(4),dp(5)); return v;
    }
    private GradientDrawable background(int color) {
        GradientDrawable d = new GradientDrawable(); d.setColor(color); d.setCornerRadius(dp(14)); return d;
    }
    private EditText input(String hint, boolean password) {
        EditText e = new EditText(this); e.setHint(hint); e.setTextColor(INK); e.setHintTextColor(Color.rgb(160,177,202));
        e.setTextSize(14); e.setPadding(dp(12),dp(10),dp(12),dp(10)); e.setBackground(background(CARD));
        e.setInputType(InputType.TYPE_CLASS_TEXT | (password ? InputType.TYPE_TEXT_VARIATION_PASSWORD : InputType.TYPE_TEXT_FLAG_MULTI_LINE));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1,-2); p.setMargins(0,dp(5),0,dp(5)); e.setLayoutParams(p);
        return e;
    }
    private Button button(String label) { Button b = new Button(this); b.setText(label); b.setAllCaps(false); b.setTextColor(ACCENT); return b; }
    private void post(Runnable r) { ui.post(() -> { if (!destroyed) r.run(); }); }
    private void controls() {
        configure.setEnabled(!busy); connect.setEnabled(!busy); address.setEnabled(!busy); code.setEnabled(!busy);
        reconnect.setVisibility(connected ? View.VISIBLE : View.GONE);
        reconnect.setEnabled(!busy);
        models.setEnabled(!busy && connected); send.setEnabled(!busy && connected && !refs.isEmpty());
        stop.setEnabled(busy && !requestId.isEmpty()); reset.setEnabled(!busy);
    }
    private String checkedAddress(String raw) throws Exception {
        String candidate = raw.trim();
        if (!candidate.contains("://")) candidate = "http://" + candidate;
        URI uri = new URI(candidate);
        String host = uri.getHost();
        if (host == null || uri.getUserInfo()!=null || uri.getQuery()!=null || uri.getFragment()!=null
                || !(uri.getPath().isEmpty() || uri.getPath().equals("/")))
            throw new Exception("Recopiez uniquement l’adresse affichée dans l’onglet Téléphone du PC.");
        if ("https".equalsIgnoreCase(uri.getScheme())) {
            String dns = host.toLowerCase(Locale.ROOT);
            // Le certificat TLS standard d'Android vérifie l'adresse *.ts.net.
            if (!dns.matches("[a-z0-9-]+\\.[a-z0-9-]+\\.ts\\.net")
                    || (uri.getPort()!=-1 && uri.getPort()!=443 && uri.getPort()!=8443))
                throw new Exception("Utilisez l’adresse HTTPS Tailscale affichée par le PC.");
            return "https://"+dns+(uri.getPort()==-1 || uri.getPort()==443 ? "" : ":"+uri.getPort());
        }
        if (!"http".equalsIgnoreCase(uri.getScheme()) || !host.matches("[0-9.]+"))
            throw new Exception("Utilisez l’adresse locale du PC ou son adresse HTTPS Tailscale.");
        InetAddress ip = InetAddress.getByName(host);
        if (!(ip instanceof Inet4Address) || !ip.isSiteLocalAddress())
            throw new Exception("L’adresse HTTP doit être celle du réseau privé local du PC.");
        int port = uri.getPort() == -1 ? 8765 : uri.getPort();
        if (port<1024 || port>65535) throw new Exception("Port invalide.");
        return "http://"+host+":"+port;
    }
    private HttpURLConnection open(String path, JSONObject body, String endpoint, String token) throws Exception {
        HttpURLConnection c = (HttpURLConnection)new URL(endpoint+path).openConnection();
        c.setInstanceFollowRedirects(false); c.setConnectTimeout(8000); c.setReadTimeout(650000);
        c.setRequestProperty("Authorization", "Bearer "+token);
        c.setRequestProperty("Accept", "application/json, application/x-ndjson");
        if (body!=null) {
            c.setRequestMethod("POST"); c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json; charset=utf-8");
            byte[] bytes=body.toString().getBytes(StandardCharsets.UTF_8);
            if (bytes.length>256*1024) throw new Exception("Discussion trop longue : commencez un nouveau chat.");
            c.setFixedLengthStreamingMode(bytes.length);
            try(OutputStream out=c.getOutputStream()) { out.write(bytes); }
        }
        return c;
    }
    private String read(InputStream stream) throws Exception {
        if (stream==null) return "";
        try (InputStream in=stream; ByteArrayOutputStream out=new ByteArrayOutputStream()) {
            byte[] buf=new byte[4096]; int n;
            while ((n=in.read(buf))!=-1) {
                if (out.size()+n>2*1024*1024) throw new IOException("Réponse trop volumineuse.");
                out.write(buf,0,n);
            }
            return out.toString("UTF-8");
        }
    }
    private void check(HttpURLConnection c) throws Exception {
        int response=c.getResponseCode();
        if (response!=200) {
            if(response==401 || response==403)
                throw new SecurityException("Code d'accès refusé. Vérifiez le nouveau code dans l'onglet Téléphone du PC.");
            String error=read(c.getErrorStream());
            try { error=new JSONObject(error).optString("error",error); } catch(JSONException ignored) {}
            if(error.isEmpty()) error="Connexion refusée (HTTP "+response+").";
            throw new IOException(error);
        }
    }
    private void connect() {
        try {
            base=checkedAddress(address.getText().toString()); secret=code.getText().toString().trim();
            if (secret.isEmpty()) throw new Exception("Saisissez le code affiché sur le PC.");
        } catch(Exception e) { status.setText(e.getMessage()); return; }
        connected=false; busy=true; controls(); status.setText("Connexion au PC…");
        final String endpoint=base, token=secret;
        final String previousRef = models.getSelectedItemPosition() >= 0 && models.getSelectedItemPosition() < refs.size()
            ? refs.get(models.getSelectedItemPosition()) : "";
        network.execute(() -> {
            HttpURLConnection c=null;
            try {
                c=open("/v1/models",null,endpoint,token); c.setReadTimeout(60000); activeConnection=c;
                check(c); JSONObject data=new JSONObject(read(c.getInputStream()));
                JSONArray list=data.getJSONArray("models");
                ArrayList<String> names=new ArrayList<>(), ids=new ArrayList<>();
                for(int i=0;i<list.length();i++) { names.add(list.getJSONObject(i).getString("label")); ids.add(list.getJSONObject(i).getString("id")); }
                String warnings=data.optJSONArray("warnings")==null ? "" : data.getJSONArray("warnings").join(" · ").replace("\"","");
                post(() -> {
                    refs.clear(); refs.addAll(ids);
                    ArrayAdapter<String> adapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_item,names);
                    adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item); models.setAdapter(adapter);
                    int restored=refs.indexOf(previousRef);
                    if(restored>=0) models.setSelection(restored);
                    connected=true; busy=false; controls();
                    connectionPanel.setVisibility(View.GONE); configure.setVisibility(View.VISIBLE);
                    android.view.inputmethod.InputMethodManager keyboard=(android.view.inputmethod.InputMethodManager)getSystemService(INPUT_METHOD_SERVICE);
                    if(keyboard!=null)keyboard.hideSoftInputFromWindow(code.getWindowToken(),0);
                    status.setText((ids.isEmpty()?"PC connecté, mais aucun modèle disponible. Lancez Ollama sur le PC.":"Connecté · "+ids.size()+" modèle(s)")+(warnings.isEmpty()?"":"\n"+warnings));
                    getPreferences(MODE_PRIVATE).edit().putString("address",endpoint).apply();
                });
            } catch(Exception e) { post(() -> { busy=false; connected=false;
                connectionPanel.setVisibility(View.VISIBLE); configure.setVisibility(View.GONE);
                status.setText("Connexion impossible : "+friendly(e)); controls(); }); }
            finally { if(c!=null)c.disconnect(); activeConnection=null; }
        });
    }
    private String friendly(Exception e) {
        if(e instanceof SecurityException) return e.getMessage();
        if(e instanceof SocketTimeoutException) return "délai dépassé. Vérifiez le PC, le Wi-Fi ou Tailscale et le pare-feu.";
        if(e instanceof ConnectException) return "PC inaccessible. Vérifiez le serveur, l’adresse et la connexion Tailscale si utilisée.";
        return e.getMessage()==null ? "échec réseau" : e.getMessage();
    }
    private TextView bubble(String who,String content) {
        TextView v=text(who+"\n"+content,15); v.setTextIsSelectable(true);
        v.setPadding(dp(12),dp(10),dp(12),dp(10)); v.setBackground(background(who.equals("VOUS")?Color.rgb(36,64,76):CARD));
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(-1,-2); p.setMargins(0,dp(6),0,dp(6));
        messages.addView(v,p); return v;
    }
    private void renderHistory() {
        messages.removeAllViews();
        if(history.length()==0) bubble("VOTRE ATELIER MOBILE","Choisissez votre modèle. Les calculs restent sur votre PC.");
        for(int i=0;i<history.length();i++) { JSONObject m=history.optJSONObject(i); if(m!=null)bubble(m.optString("role").equals("user")?"VOUS":"IA",m.optString("content")); }
        scroll.post(() -> scroll.fullScroll(View.FOCUS_DOWN));
    }
    private void send() {
        final String question=prompt.getText().toString().trim();
        if(question.isEmpty())return;
        if(question.length()>16000) { status.setText("Message trop long (16 000 caractères maximum)."); return; }
        if(models.getSelectedItemPosition()<0 || !connected)return;
        final String ref=refs.get(models.getSelectedItemPosition()), endpoint=base, token=secret;
        requestId=UUID.randomUUID().toString(); final String rid=requestId;
        cancelled=false; busy=true; controls(); prompt.setText(""); renderHistory(); bubble("VOUS",question);
        reply=bubble("IA","Préparation du modèle…"); final TextView currentReply=reply;
        status.setText("Le PC prépare la réponse…");
        final JSONArray outgoing;
        try { outgoing=new JSONArray(history.toString()); outgoing.put(new JSONObject().put("role","user").put("content",question)); }
        catch(JSONException e) { busy=false; requestId=""; controls(); return; }
        network.execute(() -> {
            StringBuilder answer=new StringBuilder(); HttpURLConnection c=null; boolean done=false; boolean stopped=false;
            try {
                JSONObject body=new JSONObject().put("model",ref).put("request_id",rid).put("messages",outgoing);
                if(cancelled)throw new IOException("Arrêt demandé.");
                c=open("/v1/chat",body,endpoint,token); activeConnection=c; check(c);
                try(BufferedReader reader=new BufferedReader(new InputStreamReader(c.getInputStream(),StandardCharsets.UTF_8))) {
                    String line; long lastUpdate=0;
                    while((line=reader.readLine())!=null) {
                        JSONObject event=new JSONObject(line); String type=event.optString("type");
                        if(type.equals("token")) {
                            answer.append(event.optString("text"));
                            if(answer.length()>512*1024)throw new IOException("Réponse trop longue.");
                            long now=System.currentTimeMillis();
                            if(now-lastUpdate>70) { String snapshot=answer.toString(); post(() -> { currentReply.setText("IA\n"+snapshot); status.setText("Réponse en cours…"); }); lastUpdate=now; }
                        } else if(type.equals("error")) throw new IOException(event.optString("message","Erreur du moteur local."));
                        else if(type.equals("done")) { done=true; stopped=event.optBoolean("stopped"); break; }
                    }
                }
                if(!done)throw new IOException("Connexion interrompue. Vous pouvez renvoyer votre message.");
                final String result=answer.toString(); final boolean interrupted=stopped;
                post(() -> {
                    currentReply.setText("IA\n"+(result.isEmpty()?"(Aucune réponse)":result));
                    if(!interrupted && !result.isEmpty()) {
                        try {
                            history.put(new JSONObject().put("role","user").put("content",question));
                            history.put(new JSONObject().put("role","assistant").put("content",result));
                            trimHistory(); if(!saveHistory())return;
                        } catch(JSONException ignored) {}
                    } else prompt.setText(question);
                    status.setText(interrupted?"Génération arrêtée · réponse partielle non enregistrée.":(history.length()==0?"Réponse terminée · trop longue pour conserver son contexte.":"Réponse terminée · historique enregistré sur le téléphone."));
                });
            } catch(Exception e) {
                String partial=answer.toString();
                post(() -> { currentReply.setText("IA\n"+(partial.isEmpty()?"Pas de réponse reçue.":partial)); prompt.setText(question);
                    if(e instanceof SecurityException || e instanceof ConnectException || e instanceof SocketTimeoutException) {
                        connected=false; connectionPanel.setVisibility(View.VISIBLE); configure.setVisibility(View.GONE);
                    }
                    status.setText(cancelled?"Génération arrêtée · vous pouvez réessayer.":friendly(e)); });
            } finally {
                if(c!=null)c.disconnect(); activeConnection=null;
                post(() -> { busy=false; requestId=""; controls(); });
            }
        });
    }
    private void cancelRequest() {
        cancelled=true; stop.setEnabled(false); status.setText("Arrêt demandé au PC…");
        final String rid=requestId, endpoint=base, token=secret;
        new Thread(() -> {
            // Retry briefly: cancellation may arrive just before the chat request.
            for(int i=0;i<6 && rid.equals(requestId);i++) {
                HttpURLConnection c=null;
                try {
                    c=open("/v1/cancel",new JSONObject().put("request_id",rid),endpoint,token);
                    c.setReadTimeout(3000); check(c);
                    if(new JSONObject(read(c.getInputStream())).optBoolean("cancelled"))break;
                    Thread.sleep(150);
                } catch(Exception ignored) { break; }
                finally { if(c!=null)c.disconnect(); }
            }
            HttpURLConnection live=activeConnection; if(live!=null && rid.equals(requestId))live.disconnect();
        },"mobile-cancel").start();
    }
    private void trimHistory() throws JSONException {
        JSONArray trimmed=new JSONArray(); int total=0;
        int first=history.length();
        for(int i=history.length()-2;i>=0;i-=2) {
            int size=history.getJSONObject(i).getString("content").length()+history.getJSONObject(i+1).getString("content").length();
            if(history.length()-i>40 || total+size>70000)break;
            total+=size; first=i;
        }
        for(int i=first;i<history.length();i++)trimmed.put(history.getJSONObject(i));
        history=trimmed;
    }
    private boolean saveHistory() {
        try(FileOutputStream out=openFileOutput("conversation.json",MODE_PRIVATE)) {
            out.write(history.toString().getBytes(StandardCharsets.UTF_8));
            return true;
        } catch(IOException e) { status.setText("Historique non enregistré : stockage indisponible."); return false; }
    }
    private void loadHistory() {
        try { history=new JSONArray(read(openFileInput("conversation.json"))); }
        catch(Exception ignored) { history=new JSONArray(); }
    }
    @Override protected void onDestroy() {
        destroyed=true;
        if(!requestId.isEmpty())cancelRequest();
        HttpURLConnection live=activeConnection; if(live!=null) new Thread(live::disconnect).start();
        network.shutdownNow();
        super.onDestroy();
    }
}
