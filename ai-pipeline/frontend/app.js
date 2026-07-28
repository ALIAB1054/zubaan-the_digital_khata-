[let mediaRecorder;
let mediaStream; 
let currentAudio = null; 
let audioChunks = [];
let currentAudioFilename = ""; 
const serverUrl = "http://127.0.0.1:8000";

const recordBtn = document.getElementById("recordBtn");
const recordStatus = document.getElementById("recordStatus");
const loadingState = document.getElementById("loadingState");
const placeholderState = document.getElementById("placeholderState");
const dataCard = document.getElementById("dataCard");
const actionControls = document.getElementById("actionControls");

window.addEventListener("DOMContentLoaded", fetchExistingLedger);

async function fetchExistingLedger() {
    try {
        const url = `${serverUrl}/get-ledger?nocache=${new Date().getTime()}`;
        const res = await fetch(url, { headers: { 'Cache-Control': 'no-store' }});
        if (res.ok) {
            const records = await res.json();
            renderLedgerTable(records);
        }
    } catch (e) { 
        console.error("Database linkage error", e); 
    }
}

recordBtn.addEventListener("click", async () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        recordBtn.classList.remove("bg-rose-600", "hover:bg-rose-700", "pulse-recording");
        recordBtn.classList.add("bg-indigo-600", "hover:bg-indigo-700");
        recordStatus.classList.add("hidden");
    } else {
        audioChunks = [];
        try {
            mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(mediaStream);
            mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
            
            mediaRecorder.onstop = async () => {
                mediaStream.getTracks().forEach(track => track.stop());
                const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
                await processAudioPipeline(audioBlob);
            };

            mediaRecorder.start();
            recordBtn.classList.remove("bg-indigo-600", "hover:bg-indigo-700");
            recordBtn.classList.add("bg-rose-600", "hover:bg-rose-700", "pulse-recording");
            recordStatus.classList.remove("hidden");
        } catch (micErr) {
            alert("Microphone permission required.");
        }
    }
});

async function processAudioPipeline(blob) {
    // Clear old forms instantly to prevent mixed data displaying
    document.getElementById("txtTranscript").innerText = "";
    document.getElementById("inpCustomer").value = "";
    document.getElementById("inpAmount").value = 0;
    document.getElementById("inpItem").value = "";

    placeholderState.classList.add("hidden");
    dataCard.classList.add("hidden");
    actionControls.classList.add("hidden");
    loadingState.classList.remove("hidden");

    const formData = new FormData();
    formData.append("audio", blob, "entry.webm");
    formData.append("speech_language", document.getElementById("speechLang").value);
    formData.append("target_language", document.getElementById("targetLang").value);

    try {
        const res = await fetch(`${serverUrl}/process-audio`, { method: "POST", body: formData });
        if (!res.ok) throw new Error("Parsing pipeline fault.");
        const data = await res.json();

        if (data.success) {
            document.getElementById("txtTranscript").innerText = data.transcript;
            document.getElementById("inpCustomer").value = data.transaction.customer || "Unknown";
            document.getElementById("inpAmount").value = data.transaction.amount || 0;
            
            const txType = String(data.transaction.type || "").toLowerCase();
            if (txType.includes("udhaar") || txType.includes("credit")) {
                document.getElementById("inpType").value = "udhaar";
            } else {
                document.getElementById("inpType").value = "cash_sale";
            }
            
            document.getElementById("inpItem").value = data.transaction.items || "None";
            document.getElementById("txtConfirmation").innerText = "Validated Successfully";
            currentAudioFilename = data.audio_filename || "";

            loadingState.classList.add("hidden");
            dataCard.classList.remove("hidden");
            actionControls.classList.remove("hidden");
        }
    } catch (err) {
        loadingState.classList.add("hidden");
        placeholderState.classList.remove("hidden");
        alert("Pipeline error parsing data.");
    }
}

document.getElementById("btnSave").addEventListener("click", async () => {
    const entry = {
        customer: document.getElementById("inpCustomer").value,
        amount: parseFloat(document.getElementById("inpAmount").value) || 0,
        type: document.getElementById("inpType").value, 
        items: document.getElementById("inpItem").value,
        transcript: document.getElementById("txtTranscript").innerText,
        audio_filename: currentAudioFilename
    };

    try {
        const res = await fetch(`${serverUrl}/save-ledger`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(entry)
        });
        
        if (res.ok) {
            await fetchExistingLedger();
            dataCard.classList.add("hidden");
            actionControls.classList.add("hidden");
            placeholderState.classList.remove("hidden");
            currentAudioFilename = "";
        }
    } catch (e) { alert("Save process error."); }
});

document.getElementById("btnCancel").addEventListener("click", () => {
    dataCard.classList.add("hidden");
    actionControls.classList.add("hidden");
    placeholderState.classList.remove("hidden");
    currentAudioFilename = "";
});

window.playAudioFile = function(filename) {
    if (!filename) return alert("Audio record unavailable.");
    if (currentAudio) currentAudio.pause();
    currentAudio = new Audio(`${serverUrl}/audios/${filename}`);
    currentAudio.play().catch(err => alert("Playback error."));
};

window.deleteRecord = async function(index) {
    if (!confirm("Delete permanently?")) return;
    try {
        const res = await fetch(`${serverUrl}/delete-ledger/${index}`, { method: "DELETE" });
        if (res.ok) {
            await fetchExistingLedger();
        }
    } catch (e) { alert("Deletion runtime link failure."); }
};

document.getElementById("btnExportCSV").addEventListener("click", () => {
    window.open(`${serverUrl}/get-ledger`, '_blank');
});

function renderLedgerTable(records) {
    const tbody = document.getElementById("ledgerBody");
    tbody.innerHTML = "";
    let totalCash = 0;
    let totalUdhaar = 0;

    if (!records || records.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-slate-400 italic">No logged entries found</td></tr>`;
        document.getElementById("summaryCash").innerText = "Rs. 0";
        document.getElementById("summaryUdhaar").innerText = "Rs. 0";
        return;
    }

    records.forEach((r, index) => {
        const isUdhaar = r.type === "udhaar";
        if (isUdhaar) totalUdhaar += r.amount; else totalCash += r.amount;

        const badgeClass = isUdhaar ? "bg-rose-100 text-rose-700 border border-rose-200" : "bg-emerald-100 text-emerald-700 border border-emerald-200";
        const typeText = isUdhaar ? "Udhaar / Credit" : "Cash Received";

        const tr = document.createElement("tr");
        tr.className = "hover:bg-slate-50/80 transition-colors border-b border-slate-100 text-sm";
        tr.innerHTML = `
            <td class="p-3 font-medium text-slate-800">${r.customer}</td>
            <td class="p-3 text-slate-500">${r.items}</td>
            <td class="p-3"><span class="px-2.5 py-1 rounded-full text-xs font-bold ${badgeClass}">${typeText}</span></td>
            <td class="p-3 font-black text-slate-700">Rs. ${r.amount}</td>
            <td class="p-3 text-center space-x-2">
                <button onclick="window.playAudioFile('${r.audio_filename}')" class="text-indigo-600 hover:text-indigo-800 font-medium mr-2 cursor-pointer">🔊 Play</button>
                <button onclick="window.deleteRecord(${index})" class="text-rose-600 hover:text-rose-800 font-bold ml-2 cursor-pointer">❌ Delete</button>
            </td>
        `;
        tbody.appendChild(tr);
    });

    document.getElementById("summaryCash").innerText = `Rs. ${totalCash}`;
    document.getElementById("summaryUdhaar").innerText = `Rs. ${totalUdhaar}`;
}]