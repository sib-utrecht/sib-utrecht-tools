import 'package:testing1/testing1.dart' as testing1;
import 'package:aws_signature_v4/aws_signature_v4.dart' as awsSig;
import 'package:aws_common/aws_common.dart';

void main(List<String> arguments) {
  print('Hello world: ${testing1.calculate()}!');

  // final signer = awsSig.AWSSigV4Signer();

  final invokeUrl = "arn:aws:lambda:eu-north-1:381492000004:function:sib-utrecht-app-CreateUploadUrlFunction-sbMdHfKfuafn";
  final region = "eu-north-1";

  

  // signer.presign(AWSHttpRequest(
  //   method: AWSHttpMethod.post,
  //   uri: Uri.parse("https://sib-utrecht-www1.s3.amazonaws.com/")),
  //   credentialScope: awsSig.AWSCredentialScope(region: "eu-north-1", service: AWSService.s3), 
    
  //   expiresIn: expiresIn)

  //   signer.sign(AWSBaseHttpRequest , credentialScope: credentialScope)
}
