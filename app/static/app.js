const $=selector=>document.querySelector(selector), $$=selector=>document.querySelectorAll(selector);
const titles={dashboard:"Dashboard",register:"Register Student",scanner:"Attendance Scanner",students:"Students",records:"Attendance Records"};

function showPage(id){
  $$(".page").forEach(element=>element.classList.remove("active"));
  $("#"+id).classList.add("active");
  $$(".nav").forEach(element=>element.classList.toggle("active",element.dataset.page===id));
  $("#pageTitle").textContent=titles[id];
  if(id==="dashboard")loadDashboard();
  if(id==="students")loadStudents();
  if(id==="records")loadRecords();
}
window.showPage=showPage;
$$(".nav[data-page]").forEach(button=>button.onclick=()=>showPage(button.dataset.page));
$("#today").textContent=new Date().toLocaleDateString(undefined,{weekday:"long",year:"numeric",month:"long",day:"numeric"});

async function requestJson(url,options){
  const response=await fetch(url,options);
  let data={};try{data=await response.json()}catch{}
  if(!response.ok)throw new Error(data.detail||"Request failed");
  return data;
}
const empty=(columns,text="No records found.")=>`<tr><td colspan="${columns}" style="text-align:center;color:#6b7280">${text}</td></tr>`;

async function loadDashboard(){
 const data=await requestJson("/api/dashboard");
 $("#totalStudents").textContent=data.total_students;
 $("#presentToday").textContent=data.present_today;
 $("#absentToday").textContent=data.absent_today;
 $("#attendanceRate").textContent=data.attendance_rate+"%";
 $("#recentTable").innerHTML=data.recent.length?data.recent.map(record=>`<tr><td>${record.roll_no}</td><td>${record.name}</td><td>${record.course}</td><td>${record.attendance_date}</td><td>${record.check_in_time}</td><td>${record.confidence}%</td></tr>`).join(""):empty(6);
}
$("#studentForm").onsubmit=async event=>{
 event.preventDefault();const message=$("#registerMessage");message.textContent="Processing face...";message.className="";
 try{const data=await requestJson("/api/students",{method:"POST",body:new FormData(event.target)});message.textContent=data.message;message.className="success";event.target.reset();loadDashboard()}
 catch(error){message.textContent=error.message;message.className="error"}
};

let allStudents=[];
async function loadStudents(){allStudents=await requestJson("/api/students");renderStudents(allStudents)}
function renderStudents(data){$("#studentTable").innerHTML=data.length?data.map(student=>`<tr><td>${student.roll_no}</td><td>${student.name}</td><td>${student.course}</td><td>${student.email||"-"}</td><td>${student.created_at}</td><td><button class="danger" onclick="deleteStudent(${student.id})">Delete</button></td></tr>`).join(""):empty(6)}
$("#studentSearch").oninput=event=>{const query=event.target.value.toLowerCase();renderStudents(allStudents.filter(student=>Object.values(student).join(" ").toLowerCase().includes(query)))};
window.deleteStudent=async id=>{if(confirm("Delete this student and attendance history?")){await requestJson(`/api/students/${id}`,{method:"DELETE"});loadStudents();loadDashboard()}};

async function loadRecords(){
 const date=$("#recordDate").value;
 const data=await requestJson("/api/attendance"+(date?`?attendance_date=${date}`:""));
 $("#downloadCsv").href="/api/reports/attendance.csv"+(date?`?attendance_date=${date}`:"");
 $("#recordTable").innerHTML=data.length?data.map(record=>`<tr><td>${record.roll_no}</td><td>${record.name}</td><td>${record.course}</td><td>${record.attendance_date}</td><td>${record.check_in_time}</td><td>${record.confidence}%</td><td><button class="danger" onclick="deleteRecord(${record.id})">Delete</button></td></tr>`).join(""):empty(7);
}
$("#filterRecords").onclick=loadRecords;
window.deleteRecord=async id=>{if(confirm("Delete this attendance record?")){await requestJson(`/api/attendance/${id}`,{method:"DELETE"});loadRecords();loadDashboard()}};

let stream;
$("#startCamera").onclick=async()=>{
 try{stream=await navigator.mediaDevices.getUserMedia({video:true});$("#video").srcObject=stream}
 catch(error){$("#scanResult").textContent="Camera permission denied.";$("#scanResult").className="result error"}
};
async function scanBlob(blob){
 const form=new FormData();form.append("photo",blob,"scan.jpg");
 const output=$("#scanResult");output.textContent="Recognizing face...";output.className="result";
 try{
   const data=await requestJson("/api/recognize",{method:"POST",body:form});
   output.textContent=data.matched?`${data.student.name} (${data.student.roll_no}) — ${data.message} Confidence: ${data.confidence}%`:data.message;
   output.className="result "+(data.matched?"success":"error");loadDashboard();
 }catch(error){output.textContent=error.message;output.className="result error"}
}
$("#capture").onclick=()=>{
 const video=$("#video"),canvas=$("#canvas");if(!video.videoWidth)return;
 canvas.width=video.videoWidth;canvas.height=video.videoHeight;
 canvas.getContext("2d").drawImage(video,0,0);canvas.toBlob(scanBlob,"image/jpeg",.92);
};
$("#scanFile").onchange=event=>{if(event.target.files[0])scanBlob(event.target.files[0])};
loadDashboard();
