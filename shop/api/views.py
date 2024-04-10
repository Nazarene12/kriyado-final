# views.py
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from shop.models import Category ,Company , Branch , Package , Offer ,Advertisement , Customer  , PackageOption  ,CustomerPackages , StoreImage , Notification , Notification_Vendor , Notification_User
from shop.api import serializers
from rest_framework.permissions import AllowAny ,IsAuthenticated
from django.db import transaction
from rest_framework.views import APIView
from user.api.serializers import CustomUserSerializer,ValidateEmailSerializer
from user.api.utils import generate_random_password , send_confirmation_email , send_verification_email
from user.variable import USER,VENDOR,ADMIN
from user.api.permissions import IsAdminUserType ,IsNotAdminType,IsUserType,IsAdminOrVendor,IsVendorType
from django.http import Http404
from datetime import timedelta,datetime
from shop.variables import REGISTER , CONTACT , UPDATE , DELETE
from drf_standardized_errors.handler import exception_handler
from shop.api import filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db import transaction
from django.contrib.auth.hashers import make_password
from django.contrib.sessions.models import Session
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.contrib.sessions.backends.db import SessionStore
from rest_framework.decorators import api_view , permission_classes
from django.db.models import F
from notification.models import ConfigValue


""" CATEGORY VIEW SECTION """

class CategoryListView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [SearchFilter , DjangoFilterBackend ,OrderingFilter]
    search_fields = ["name"]
    filterset_class = filters.CategoryFilter
    ordering_fields = ['name']

class CategoryDetailView(generics.RetrieveAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [IsAdminUserType]

class CategoryCreateView(generics.CreateAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes=[IsAdminUserType]

class CategoryUpdateView(generics.UpdateAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [IsAdminUserType]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if not instance.is_active:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class CategoryDeleteView(generics.DestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [IsAdminUserType]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

"""END OF CATEGORY """


""" PACKAGE VIEW SECTION """

class PackageListView(generics.ListCreateAPIView):
    queryset = Package.objects.all()
    serializer_class = serializers.PackageViewSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ["name"]

class Package_OptionsListView(generics.ListCreateAPIView):  # all  packages with its available options 
    queryset = Package.objects.all()
    serializer_class = serializers.package_OptionViewSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query_set = Package.objects.filter(is_active = True)
        return query_set

class PackageCreateView(generics.CreateAPIView):
    queryset = Package.objects.all()
    serializer_class = serializers.PackageSerializer
    permission_classes=[IsAdminUserType]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        pakage_type = request.data.pop("options",None)
        if not pakage_type or len(pakage_type) == 0:
            return Response({"error":"cannot able to create the package without options"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        package_id = serializer.data.get("id")
        for each in pakage_type:
            each["package_detail"] = package_id
        option_serializer = serializers.PackageOptionCreateSerializer(data=pakage_type , many=True ,  context={'request': request})
        option_serializer.is_valid(raise_exception=True)
        option_serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class PackageDetailView(generics.RetrieveAPIView):
    queryset = Package.objects.all()
    serializer_class = serializers.PackageViewSerializer
    permission_classes = [IsAuthenticated]

class PackageUpdateView(generics.UpdateAPIView):
    queryset = Package.objects.all()
    serializer_class = serializers.PackageSerializer
    permission_classes = [IsAdminUserType]

class PackageDeleteView(generics.DestroyAPIView):
    queryset = Package.objects.all()
    serializer_class = serializers.PackageSerializer
    permission_classes = [IsAdminUserType]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

class PackageOptionCreateView(generics.CreateAPIView):
    queryset = PackageOption.objects.all()
    serializer_class = serializers.PackageOptionCreateSerializer
    permission_classes=[IsAdminUserType]
   
class PackageOptionUpdateView(generics.UpdateAPIView):
    queryset = PackageOption.objects.all()
    serializer_class = serializers.PackageOptionCreateSerializer
    permission_classes = [IsAdminUserType]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if not instance.is_active:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class PackageOptionDeleteView(generics.DestroyAPIView):
    queryset = PackageOption.objects.all()
    serializer_class = serializers.PackageSerializer
    permission_classes = [IsAdminUserType]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

class PackageOptionListView_User(generics.ListCreateAPIView):
    queryset = PackageOption.objects.all()
    serializer_class = serializers.PackageOptionListSerializer_User
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = filters.PackageOptionFilter
    def get_queryset(self):
        return PackageOption.objects.filter(is_active=True , package_detail__is_active =True)


"""END OF PACKAGE """

""" CUSTOMER VIEW SECTION """

class CustomerCreateView(APIView):
    permission_classes = [IsAdminUserType]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        data = request.data if request.data.get("image") else request.data.copy()
        email = request.data['email_id']
        number = request.data["number"]
        user_serializer = serializers.CustomUserSerializer_Admin(data={'username': email , "password" :number , "type" : USER})
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        data["user"] = user.id
        customer_serializer = serializers.CustomerSerializer(data=data)
        customer_serializer.is_valid(raise_exception=True)
        customer = customer_serializer.save()
        data["user"]= customer.id
        package_serializer = serializers.CustomerPackagesSerializer(data=data)
        package_serializer.is_valid(raise_exception=True)
        package_serializer.save()
        return Response(customer_serializer.data, status=status.HTTP_201_CREATED) 

class CustomerDetailView_Admin(generics.RetrieveAPIView):
    queryset = Customer.objects.all()
    serializer_class = serializers.CustomerSerializer_Admin
    permission_classes = [IsAdminUserType]

class CustomerListView_Admin(generics.ListCreateAPIView):
    # queryset = Customer.objects.all()
    serializer_class = serializers.CustomerListSerializer_Admin
    permission_classes = [IsAdminUserType]
    filter_backends = [SearchFilter , DjangoFilterBackend]
    filterset_class = filters.CustomerFilter
    search_fields = ["name","email_id","district","number"]

    def get_queryset(self):
        return Customer.objects.exclude(user__user_type=ADMIN)

class CustomerUpdateDetailView(generics.GenericAPIView):
    
    permission_classes = [IsUserType]
    serializer_class = serializers.CustomerDetailUpdateSerializer_User

    def get_queryset(self):
        return Customer.objects.get(user=self.request.user)
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset() 
        serializer = self.get_serializer(queryset) 
        return Response(serializer.data) 
    
    def put(self, request, *args, **kwargs):
        queryset = self.get_queryset() 
        serializer = self.get_serializer(queryset,data=request.data) 
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

class CustomerUpdateProfilePhotoView_User(generics.UpdateAPIView):
    queryset = Customer.objects.all()
    serializer_class = serializers.CustomerProfilePhotoUpdateSerializer
    permission_classes = [IsUserType]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if not instance.user.is_active or instance.image:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(image=request.FILES.get('image'))
        return Response(serializer.data)

class QuickCustomerDetailView(generics.GenericAPIView):

    serializer_class = serializers.QuickCustomerDetailSerializer
    permission_classes = [IsUserType]

    def get_queryset(self):
        return Customer.objects.get(user=self.request.user)
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset() 
        serializer = self.get_serializer(queryset) 
        return Response(serializer.data) 
    

"""not verified """
class CustomerPackageUpdateView(generics.CreateAPIView):
    queryset = CustomerPackages.objects.all()
    serializer_class = serializers.CustomerPackagesSerializer
    permission_classes=[IsAdminUserType]

""" END OF CUSTOMER """  

        
"""VENDOR VIEW COMPANY SECTION """


class CompanyListView(generics.ListCreateAPIView):
    queryset = Company.objects.all()
    serializer_class = serializers.CompanyListSerializer
    permission_classes = [IsAdminUserType]
    filter_backends = [SearchFilter]
    search_fields = ["organization","owner"]

# from django.core.files.uploadedfile import InMemoryUploadedFile

class CompanyCreateView(generics.CreateAPIView):
    queryset = Company.objects.all()
    serializer_class = serializers.CompanySerializer
    permission_classes = [AllowAny]

    def get_exception_handler(self):
        return exception_handler

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        user_serializer = ValidateEmailSerializer(data={'username': request.data["email_id"]})
        user_serializer.is_valid(raise_exception=True)
        data = request.data if request.data.get("logo") or request.data.get("image[]") else request.data.copy()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        company_id = serializer.data.get('id')
        data['company'] = company_id
        branch_serializer = serializers.BranchSerializer(data=data)
        branch_serializer.is_valid(raise_exception=True)
        branch = branch_serializer.save(head_office = True)
        images_data =[]
        for file in request.FILES.getlist('image[]'):
            data = {'image': file, 'branch': branch.id}
            images_data.append(data)
            
        image_serializer = serializers.StoreImageSerializer(data=images_data, many=True)
        image_serializer.is_valid(raise_exception=True)
        image_serializer.save()
        
        return Response({"id": company_id}, status=status.HTTP_201_CREATED)
        
class CompanyDetailView(generics.RetrieveAPIView):
    queryset = Company.objects.all()
    serializer_class = serializers.CompanySerializer
    permission_classes = [IsAdminOrVendor]

class CompanyDetailView_Vendor(APIView):
    serializer_class = serializers.CompanySerializer
    permission_classes = [IsAdminOrVendor]

    def get(self,request):
        serializer = self.serializer_class(request.user.detail_v)
        return Response(serializer.data, status=status.HTTP_200_OK)


    
# class OfferCreateAPIView(APIView):

#     permission_classes=[IsAdminOrVendor]

#     @transaction.atomic
#     def post(self, request):
#         is_bulk = isinstance(request.data, list)
#         serializer = serializers.OfferSerializer(data=request.data , many=is_bulk)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         transaction.set_rollback(True)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




class CompanyUpdateView(generics.UpdateAPIView):
    queryset = Company.objects.all()
    serializer_class = serializers.CompanyUpdateSerializer
    permission_classes = [IsVendorType]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if not instance.is_registered:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class CompanyLogoUpdateView(generics.UpdateAPIView):
    queryset = Company.objects.all()
    serializer_class = serializers.CompanySerializer
    permission_classes = [IsVendorType]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        if not instance.is_registered:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)
    
class CompanyDeleteView(generics.DestroyAPIView):
    queryset = Company.objects.all()
    serializer_class = serializers.CompanySerializer
    permission_classes = [IsAdminUserType]

    def perform_destroy(self, instance):
        instance.is_registered = False
        instance.save()
        obj = instance.branches.all()
        obj.update(is_active = False)

@api_view(['POST'])
@permission_classes([IsAdminUserType])
def CompanyVerification(request,pk):
    

    if request.method =="POST":
        try:
            obj = Company.objects.get(pk = pk)
        except Company.DoesNotExist:
            return Response({'error': 'Invalid or expired session'}, status=status.HTTP_400_BAD_REQUEST)
        user_serializer = serializers.CustomUserSerializer_Admin(data={'username': obj.email_id , "password" :obj.mobile_number , "type" : VENDOR})
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        obj.is_registered = True
        obj.join_date = datetime.now()
        obj.user = user
        obj.save()
        # s = SessionStore()
        # s["user_id"] = user.id
        # s.create()
        # s.set_expiry(300)
        # session_key = s.session_key
        # try:
        #     send_verification_email(obj.email_id , obj.owner , session_key)
        # except:
        #     return Response({'error':'there is an error in the server for sending the email to user.'}, status=status.HTTP_409_CONFLICT)
        return Response({"success","verification email send successfull"}, status=status.HTTP_201_CREATED)

class CompanyRegistrationAPIView(APIView):
    def post(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        company.is_registered = True
        company.save()
        try:
            send_confirmation_email(company.email_id , company.owner)
        except:
            return Response({'error':'there is an error in the server for sending the email to user.'}, status=status.HTTP_409_CONFLICT)
        return Response({'success': 'Company registered successfully'}, status=status.HTTP_200_OK)
    
"""not verified"""      
class CompanyBranchListView(generics.ListAPIView):

    serializer_class = serializers.BranchIDSerializer
    permission_classes = [AllowAny]
    authentication_classes =[]

    def get_queryset(self):
        company_id = self.kwargs['company_id']
        return Branch.objects.filter(company_id=company_id)
    

"""END SECTION COMPANY"""    


"""VENDOR VIEW BRANCH SECTION """

class BranchCreateView(generics.CreateAPIView):
    queryset = Branch.objects.all()
    serializer_class = serializers.BranchSerializer
    permission_classes = [AllowAny]

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            branch_id = serializer.data.get('id')
            images_data =[]
            for file in request.FILES.getlist('image[]'):
                data = {'image': file, 'branch': branch_id}
                images_data.append(data)

            image_serializer = serializers.StoreImageSerializer(data=images_data, many=True)
            image_serializer.is_valid(raise_exception=True)
            image_serializer.save()
            return Response({"id": branch_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            transaction.set_rollback(True)
            return Response(e.args[0], status=status.HTTP_400_BAD_REQUEST)     

class BranchListView(generics.ListCreateAPIView):
    queryset = Branch.objects.all()
    serializer_class = serializers.BranchSerializer
    permission_classes = [AllowAny]

class BranchDetailView(generics.RetrieveAPIView):
    queryset = Branch.objects.all()
    serializer_class = serializers.BranchSerializer
    permission_classes = [AllowAny]

class BranchUpdateView(generics.UpdateAPIView):
    queryset = Branch.objects.all()
    serializer_class = serializers.BranchSerializer
    permission_classes = [IsVendorType]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.is_active:
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
        request.data["company"] = instance.company.id
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class BranchDeleteView(generics.DestroyAPIView): 
    queryset = Notification.objects.all()
    serializer_class = serializers.NotificationBranchSerializer
    permission_classes = [IsAdminUserType]

    def perform_destroy(self, instance):
        instance.Branch_id.is_active = False
        instance.Branch_id.save()
        instance.approved = True
        instance.save()
        message = f"Admin have accepted the request to delete the branch in {instance.Branch_id.Locality}."
        Notification_Vendor.objects.create(message =message , user = instance.Branch_id.company )
        instance.save()
        self.send_notification_broadcast()

    def send_notification_broadcast(self):
        channel_layer = get_channel_layer()
        
        group_name = "Notification_AUU" 

        async_to_sync(channel_layer.group_send)(
            group_name, {
                'type': 'notification_AUU', 
                'increment': 1 
            }
        )

class BranchListViewCustomer(generics.ListAPIView):
    queryset = Branch.objects.all()
    serializer_class = serializers.BranchCustomerSerializer
    permission_classes = [IsUserType]
    filter_backends = [DjangoFilterBackend,SearchFilter]
    filterset_class = filters.BranchFilter
    search_fields = ['company__organization' , 'District' , 'Locality']

    def get_queryset(self):
        user = self.request.user.detail_c
        customer_package = user.package_c.filter(is_active = True).first()
        package = customer_package.package.package_detail
        categories = package.categories.all()
        queryset = Branch.objects.filter(category__in=categories)
        return queryset
    
class BranchListViewVendor(generics.ListAPIView):
    queryset = Branch.objects.all()
    serializer_class = serializers.BranchCustomerSerializer_Vendor
    permission_classes = [IsVendorType]

    def get_queryset(self):
        queryset = Branch.objects.filter(company = self.request.user.detail_v)
        return queryset

class BranchDetailViewCustomer(generics.RetrieveAPIView):
    queryset = Branch.objects.all()
    serializer_class = serializers.BranchDetailCustomerSerializer
    permission_classes = [IsUserType]

"""END SECTION VIEW """

"""VENDOR VIEW IMAGE SECTION"""

class ImageDeleteView(generics.DestroyAPIView):
    queryset = StoreImage.objects.all()
    serializer_class = serializers.StoreImageSerializer
    permission_classes = [IsAdminUserType]

class ImageCreateView(generics.CreateAPIView):
    queryset = StoreImage.objects.all()
    serializer_class = serializers.StoreImageSerializer
    permission_classes = [IsAdminUserType]

    
"""END SECTION VIEW"""

"""OFFER VIEW FUNCTIONS FOR CRUD OPERATIONS"""

class OfferListAPIView(APIView):

    permission_classes=[IsAuthenticated]

    def get(self, request, pk):
        branch = get_object_or_404(Branch, pk=pk)
        offers = Offer.objects.filter(branch=branch)
        serializer = serializers.OfferSerializer(offers, many=True)
        return Response(serializer.data ,status=status.HTTP_200_OK)


class OfferCreateAPIView(APIView):

    permission_classes=[AllowAny]

    @transaction.atomic
    def post(self, request):
        is_bulk = isinstance(request.data, list)
        serializer = serializers.OfferSerializer(data=request.data , many=is_bulk)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        transaction.set_rollback(True)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
class NotificationAprovalAPIView(APIView):

    permission_classes = [IsAdminUserType]

    def get_object(self, pk ):
        try:
            return Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            raise Http404


    @transaction.atomic
    def put(self, request, pk ):

        obj = self.get_object(pk)
        if not obj.offer_id or obj.approved or obj.notification_type != "UPDATE_O":
            return Response({"error" : "invalid"}, status=status.HTTP_400_BAD_REQUEST)
        obj.approved = True
        message_u = f"{obj.offer_id.branch.company.organization} has update the offer {obj.offer_id.offer} to {obj.new_offer}"
        message_v = f"Admin has accepted the request to update the offer to {obj.new_offer}"
        Notification_Vendor.objects.create(message = message_v , user = obj.user.detail_v)
        Notification_User.objects.create(message = message_u)
        serializer = serializers.OfferUpdateSerializer(obj.offer_id, data={"offer": obj.new_offer} ,partial = True)
        if serializer.is_valid():
            serializer.save()
            obj.save()
            self.send_notification_broadcast()
            return Response(serializer.data,status=status.HTTP_200_OK)
        transaction.set_rollback(True)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @transaction.atomic
    def delete(self, request, pk ):
        
        obj = self.get_object(pk)
        if not obj.offer_id or obj.approved or obj.notification_type != "DELETE_O":
            return Response({"error" : "invalid"}, status=status.HTTP_400_BAD_REQUEST)
        obj.approved = True
        message_u = f"{obj.offer_id.branch.company.organization} has delete the offer {obj.offer_id.offer}"
        message_v = f"Admin has accepted the request to delete the offer to {obj.offer_id.offer}"
        Notification_Vendor.objects.create(message = message_v , user =  obj.user.detail_v)
        Notification_User.objects.create(message = message_u)
        obj.save()
        obj.offer_id.delete()

        
        self.send_notification_broadcast()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    def send_notification_broadcast(self):
        channel_layer = get_channel_layer()
        
        group_name = "Notification_AUU" 

        async_to_sync(channel_layer.group_send)(
            group_name, {
                'type': 'notification_AUU', 
                'increment': 1 
            }
        )
   

class AdvertisementCreateView(generics.CreateAPIView):
    queryset = Advertisement.objects.all()
    serializer_class = serializers.AdvertisementSerializer
    permission_classes = [IsVendorType]

    def perform_create(self, serializer):
        print(self.request.data)
        data = self.request.data
        creation_date = datetime.now().date() if 'creation_date' not in data else datetime.strptime(data['creation_date'], '%Y-%m-%d').date()
        expiry_date =creation_date + timedelta(days=1) if 'expiry_date' not in data else data['expiry_data']
        serializer.save(expiry_date=expiry_date , creation_date = creation_date)


from django.utils import timezone
class AdvertisementCreateView_Admin(generics.CreateAPIView):
    queryset = Advertisement.objects.all()
    serializer_class = serializers.AdvertisementSerializer_Admin
    permission_classes = [IsAdminUserType]

    def perform_create(self, serializer):
        data = self.request.data
        # Use timezone.now() instead of datetime.now() for timezone-aware datetime
        creation_date = timezone.now().date() if 'creation_date' not in data or data["creation_date"] =="" else timezone.datetime.strptime(data['creation_date'], '%Y-%m-%d').date()
        # Correctly handle 'expiry_date' key
        expiry_date = creation_date + timedelta(days=1) if 'expiry_date' not in data or data["expiry_date"] =="" else timezone.datetime.strptime(data['expiry_date'], '%Y-%m-%d').date()
        serializer.save(expiry_date=expiry_date, creation_date=creation_date)
        
class AdvertisementListView(generics.ListAPIView):
    queryset = Advertisement.objects.all()
    serializer_class = serializers.AdvertisementSerializer
    permission_classes =[IsAdminUserType]

class AdvertisementListViewCustomer(generics.ListAPIView):
    queryset = Advertisement.objects.all()
    serializer_class = serializers.AdvertisementSerializer
    permission_classes = [IsUserType]

    def get_queryset(self):
        queryset = Advertisement.objects.filter(expiry_date__gte = datetime.now())
        return queryset
    
class AdvertisementListViewVendor(generics.ListAPIView):
    queryset = Advertisement.objects.all()
    serializer_class = serializers.AdvertisementSerializer
    permission_classes = [IsVendorType]

    def get_queryset(self):
        branch = self.request.user.detail_v.branches.all()
        queryset = Advertisement.objects.filter(branch__in = branch)
        return queryset

class AdvertisementDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Advertisement.objects.all()
    serializer_class = serializers.AdvertisementSerializer
    permission_classes=[IsAdminOrVendor]

    
class NotificationCreateAPIView(APIView):

    permission_classes = [IsNotAdminType]

    def post(self, request, *args, **kwargs):

        serializer = serializers.NotificationSerializer(data=request.data)

        if (not request.user.is_authenticated and request.data['notification_type'] == "REGISTER_C" ) or (request.user.is_authenticated and ((request.user.user_type == USER and request.data['notification_type'] == CONTACT ) or (request.user.user_type == VENDOR and request.data['notification_type'] in ["UPDATE_O" , "DELETE_O" , "DELETE_C" , "DELETE_B"]))) :

            if serializer.is_valid():
                serializer.save(user=request.user)
                self.send_notification_broadcast()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error":"unautherized action"}, status=status.HTTP_400_BAD_REQUEST)
    
    def send_notification_broadcast(self):
        channel_layer = get_channel_layer()
        # Assuming you have a group for all connected users
        group_name = "notification_CNOT"  # Use the room name from the notification

        async_to_sync(channel_layer.group_send)(
            group_name, {
                'type': 'notification_message', # Matches the method name in the consumer
                'message': 'New notification created' # Assuming Notification has a title
            }
        )

class NotificationRegisterAPIView(generics.CreateAPIView):

    permission_classes = [AllowAny]
    queryset = Notification.objects.all()
    serializer_class = serializers.NotificationRegisterSerializer


    def perform_create(self, serializer):
        company = self.request.data["register_id"]
        try:
            obj = Company.objects.get(pk = company)
        except Company.DoesNotExist:
            raise Http404
        message = f"{obj.organization} has has requested to register ."
        serializer.save(notification_type = "REGISTER_C",message=message)
        self.send_notification_broadcast()
        return Response({"success" :"register successful"}, status=status.HTTP_200_OK)

    def send_notification_broadcast(self):
        channel_layer = get_channel_layer()
        
        group_name = "Notification_RVM" 

        async_to_sync(channel_layer.group_send)(
            group_name, {
                'type': 'notification_RVM', 
                'increment': 1 
            }
        )

class NotificationBranchAPIView(generics.CreateAPIView):

    permission_classes = [IsVendorType]
    queryset = Notification.objects.all()
    serializer_class = serializers.NotificationBranchSerializer


    def perform_create(self, serializer):
        branch = self.request.data["Branch_id"]
        try:
            obj = Branch.objects.get(pk = branch)
        except Branch.DoesNotExist:
            raise Http404
        message = f"{obj.company.organization} is request to delete branch in locality {obj.Locality}."
        serializer.save(notification_type="DELETE_B" , message=message , user=self.request.user)
        self.send_notification_broadcast()
        return Response({"success" :"successful"}, status=status.HTTP_200_OK)

    def send_notification_broadcast(self):
        channel_layer = get_channel_layer()
        
        group_name = "Notification_RVM" 

        async_to_sync(channel_layer.group_send)(
            group_name, {
                'type': 'notification_RVM', 
                'increment': 1 
            }
        )


class NotificationOfferUpdateAPIView(generics.CreateAPIView):

    permission_classes = [IsVendorType]
    queryset = Notification.objects.all()
    serializer_class = serializers.NotificationOfferUpdateSerializer


    def perform_create(self, serializer):
        offer= self.request.data["offer_id"]
        # print(self.request.data)
        try:
            obj = Offer.objects.get(pk = offer)
        except Offer.DoesNotExist:
            raise Http404
        message = f"{obj.branch.company.organization} is request to update offer in branch locality {obj.branch.Locality}."
        serializer.save(notification_type="UPDATE_O" , message=message , user=self.request.user)
        self.send_notification_broadcast()
        return Response({"success" :"successful"}, status=status.HTTP_200_OK)

    def send_notification_broadcast(self):
        channel_layer = get_channel_layer()
        
        group_name = "Notification_RVM" 

        async_to_sync(channel_layer.group_send)(
            group_name, {
                'type': 'notification_RVM', 
                'increment': 1 
            }
        )

class NotificationOfferDeleteAPIView(generics.CreateAPIView):

    permission_classes = [IsVendorType]
    queryset = Notification.objects.all()
    serializer_class = serializers.NotificationOfferDeleteSerializer


    def perform_create(self, serializer):
        offer= self.request.data["offer_id"]
        try:
            obj = Offer.objects.get(pk = offer)
        except Offer.DoesNotExist:
            raise Http404
        message = f"{obj.branch.company.organization} is request to delete offer in branch locality {obj.branch.Locality}."
        serializer.save(notification_type="DELETE_O" , message=message , user=self.request.user)
        self.send_notification_broadcast()
        return Response({"success" :"successful"}, status=status.HTTP_200_OK)

    def send_notification_broadcast(self):
        channel_layer = get_channel_layer()
        
        group_name = "Notification_RVM" 

        async_to_sync(channel_layer.group_send)(
            group_name, {
                'type': 'notification_RVM', 
                'increment': 1 
            }
        )

class NotificationListViewCustomer(generics.ListAPIView):
    queryset = Notification_User.objects.all()
    serializer_class = serializers.NotificationListSerializer__User
    permission_classes = [IsUserType]

    def get_queryset(self):
        queryset = Notification_User.objects.all()
        user = self.request.user.detail_c
        user.notification_count = queryset.count()
        user.save()
        return queryset

         
@api_view(['GET'])
@permission_classes([IsUserType])
def notification_count_user(request):

    three_days_ago = datetime.now() - timedelta(days=3)
    old_queryset = Notification_User.objects.filter(created_date__lte=three_days_ago)
    number = old_queryset.count()
    old_queryset.delete()
    delete_count = ConfigValue.objects.get(id=1)
    delete_count.value = delete_count.value + number
    delete_count.save()
    user = request.user.detail_c
    user_seen = user.notification_count
    count = Notification_User.objects.count()
    if user_seen > delete_count.value:
        count = ( delete_count.value + count ) - user_seen

    return Response({'notification_count': count})      
    
   
class NotificationListViewVendor(generics.ListAPIView):
    queryset = Notification.objects.all()
    serializer_class = serializers.NotificationListSerializer__Vendor
    permission_classes = [IsVendorType]

    def get_queryset(self):
        user = self.request.user.detail_v
        queryset = Notification_Vendor.objects.filter(user = user)  
        user.notification_count = queryset.count()
        user.save()
        return queryset

@api_view(['GET'])
@permission_classes([IsVendorType])
def notification_count_vendor(request):

    three_days_ago = datetime.now() - timedelta(days=3)
    old_queryset = Notification_Vendor.objects.filter(created_date__lte=three_days_ago , user = request.user.detail_v)
    number = old_queryset.count()
    old_queryset.delete()
    user = request.user.detail_v
    user_seen = user.notification_count
    count = Notification_Vendor.objects.filter(user = request.user.detail_v).count()
    if user_seen >= (count + number):
        count = 0

    return Response({'notification_count': count})  

class NotificationListViewAdmin(generics.ListAPIView):
    queryset = Notification.objects.all()
    serializer_class = serializers.NotificationSerializer
    permission_classes = [IsAdminUserType]

    def get_queryset(self):
        user = self.request.user.detail_c
        queryset = Notification.objects.all()  
        user.notification_count = queryset.count()
        user.save()
        return queryset
        

@api_view(['GET'])
@permission_classes([IsAdminUserType])
def notification_count_admin(request):

    seven_days_ago = datetime.now() - timedelta(days=7)
    old_queryset = Notification.objects.filter(created_date__lte=seven_days_ago )
    number = old_queryset.count()
    old_queryset.delete()
    user = request.user.detail_c
    user_seen = user.notification_count
    count = Notification.objects.count()
    if user_seen >= (count + number):
        count = 0

    return Response({'notification_count': count})  

# class OfferDetailAPIView(APIView):

#     permission_classes = [IsAdminUserType]

#     def get_object(self, pk):
#         try:
#             return Offer.objects.get(pk=pk)
#         except Offer.DoesNotExist:
#             raise Http404

#     def get(self, request, pk):
#         offer = self.get_object(pk)
#         serializer = serializers.OfferSerializer(offer)
#         return Response(serializer.data ,status=status.HTTP_200_OK)

#     @transaction.atomic
#     def put(self, request, pk , id):
#         try:
#             obj = Notification.objects.get(pk = id)
#         except Notification.DoesNotExist:
#             Http404
#         offer = self.get_object(pk)
#         obj.approved = True
#         obj.admin_replay_user = f"{offer.branch.company.organization} has update the offer {offer.offer} to {}"
#         obj.save()
#         serializer = serializers.OfferUpdateSerializer(offer, data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data,status=status.HTTP_200_OK)
#         transaction.set_rollback(True)
#         self.send_notification_broadcast()
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#     @transaction.atomic
#     def delete(self, request, pk , id):
#         try:
#             obj = Notification.objects.get(pk = id)
#         except Notification.DoesNotExist:
#             Http404
#         offer = self.get_object(pk)
#         obj.approved = True
#         obj.admin_replay_user = f"{offer.branch.company.organization} has delete the offer {offer.offer}"
#         obj.save()
#         offer.delete()
        
#         self.send_notification_broadcast()
#         return Response(status=status.HTTP_204_NO_CONTENT)
    
#     def send_notification_broadcast(self):
#         channel_layer = get_channel_layer()
        
#         group_name = "Notification_AUU" 

#         async_to_sync(channel_layer.group_send)(
#             group_name, {
#                 'type': 'notification_AUU', 
#                 'increment': 1 
#             }
#         )
        