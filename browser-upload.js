import {Upload} from 'tus-js-client';
export async function uploadPhoto(file, ticket, onProgress) {
  if(ticket.complete)return ticket.id;
  return new Promise((resolve, reject) => {
    const upload = new Upload(file, {
      endpoint: ticket.endpoint, headers: {'x-signature':ticket.token},
      chunkSize:6*1024*1024, uploadDataDuringCreation:true,
      retryDelays:[0,1000,3000,5000], removeFingerprintOnSuccess:true,
      fingerprint:async()=>`minhwa-${ticket.id}`,
      metadata:{bucketName:ticket.bucket, objectName:ticket.path, contentType:file.type || 'image/heic', cacheControl:'0'},
      onProgress:(sent,total)=>onProgress(Math.round(sent/total*100)),
      onError:()=>reject(new Error('The photo upload was interrupted. Please retry with the same photo.')),
      onSuccess:()=>resolve(ticket.id),
    });
    upload.findPreviousUploads().then(previous=>{
      if(previous.length)upload.resumeFromPreviousUpload(previous[0]);
      upload.start();
    }).catch(()=>reject(new Error('Could not prepare your upload. Please try again.')));
  });
}
